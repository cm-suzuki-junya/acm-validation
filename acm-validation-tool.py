import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))

import boto3, fire
import csv

class Main:
    '''ACMの検証保留中のレコードの一括出力/登録ツール

        SubCommand:
            export: 標準出力にcsv形式でレコードを出力する
            regist: 指定したcsvファイルからRoute53にレコードを登録
        
        Examples:
            python3 acm-validation-tool.py export
            python3 acm-validation-tool.py regist export.csv
        
        Args:
            profile (str): 実行時に利用するAWSプロファイル
            region (str): 実行先リージョン
            dry (bool): Trueの場合、確認メッセージの出力後の登録処理を行いません
    '''
    #TODO: 初期化処理がi/oセットになってるので分離したい
    def __init__(self, profile: str="default", region: str="", dry: bool=False):
        session = boto3.Session(profile_name=profile)
        self._acm = session.client("acm")
        self._route53 = session.client("route53")
        self._csv_header = ["Domain", "Name", "Type", "Value"]
        self._dry = dry
    
    def regist(self, file: str):
        '''
            FILEをCSVとして読み込みRoute 53にレコードを登録します。

            CSVに記載されたレコードはRoute53のゾーンの内ゾーン名が最長で一致するゾーンに登録を行います。
            該当ゾーンに同名レコードが登録されている場合は上書きします。

            ** WARNING **
                検証が十分に行われていないため状態により想定しないゾーンにレコードが登録される可能性があります。
                事前に--dryオプションを利用して登録レコードと登録先Zoneを確認してください。
            
            Examples:
                python3 acm-validation-tool.py regist export.csv
        '''
        with open(file, "r") as f:
            for record in csv.DictReader(f):
                print("[Start] Domain: {}".format(record["Domain"]))
                zone = self._get_longest_match_zone_id(record["Domain"])
                if zone == dict():
                    print("Not fond hosted zone.")
                    continue
                self._regist_to_zone(record, zone) 
    def export(self):
        '''
            保留中のACMの認証レコードを出力する

            Examples:
                python3 acm-validation-tool.py export
        '''
        result = []
        cert_list = self._acm.list_certificates()

        if 0 == len(cert_list):
            print("no certificate")
            return
        
        for cert in cert_list['CertificateSummaryList']:
            try:
                record = self._list_pending_validation_record(cert['CertificateArn'])
                if 0 != len(record):
                    result.extend(record)
            except Exception as e:
                print("Raise error in '{}' process : {}".format(
                    cert['CertificateArn'], e
                ), file=sys.stderr)
        
        if 0 == len(result):
            print("Found certificate. But there are no records with 'PENDING_VALIDATION' status.")

        #CSV形式でstdoutに出力
        print(",".join(self._csv_header))
        for res in result:
            print(",".join(list(res.values())))
    
    def _list_pending_validation_record(self, cert_arn: dict) -> list:
        '''
            引数に指定した証明書のARNからその中の保留中のレコードの一覧を返却する
            Return example:
                [{
                    'Domain': 'example.com',
                    'Name': '_hogehoge.example.com',
                    'Type': 'CNAME',
                    'Value': '_foo.bar.acm-validations.aws.'
                }]

        '''
        result = []
        detail = self._acm.describe_certificate(CertificateArn=cert_arn)
        for domain in detail['Certificate']['DomainValidationOptions']:
            if 'PENDING_VALIDATION' == domain['ValidationStatus']:
                # boto3側の返却値の順番補償が不明なので一度出力して吸収しておく
                res = {
                    'Domain': domain['DomainName'],
                    'Name': domain['ResourceRecord']['Name'],
                    'Type': domain['ResourceRecord']['Type'],
                    'Value': domain['ResourceRecord']['Value']
                }
                result.append(res)
        return result
    
    def _get_longest_match_zone_id(self, domain: str)-> dict:
        '''
            受け取ったドメインと最長で一致するドメインとそのホストゾーンIDを返却する
            複数同名のZoneが取得された場合は取得順となるゾーン情報を返却します
            Return Example:
                {
                    'Id': 'XXXXXXXX'
                    'Name': 'example.com',
                }
        '''
        #同一名のZoneが複数存在する可能性あるので配列で受け入れて加工して最後にdictにする
        result = []
        splited_domain = domain.split(".")
        #.区切られてないドメインは不正なドメインと判定する
        if 2 > len(splited_domain):
            print("Invalid Domain {}".fomart(domain), file=sys.stderr)
            return dict()
        
        #HACK: 全権取得するのでコストが高いlist_hosted_zones_by_name()の挙動はよくわからなかった
        #      2000件以上は対応していないです。
        zone_list = self._route53.list_hosted_zones()
        if 0 == len(zone_list['HostedZones']):
            return dict()
        
        # 取得元のホストを元から徐々に先頭を減らしていき一致するまで検索をかける
        # ただし最短は2要素まで
        # a.b.c.com -> b.c.com -> c.com
        # HACK: 全取得結果全てに対して毎回filterをかけるのでコストが高い
        #         =>　逆に要素を増やして徐々に絞り込む方がコストは低そう
        for i in range(0, len(splited_domain) - 1):
            target_host = ".".join(splited_domain[i:]) + "."
            target_zones = [ zone for zone in zone_list['HostedZones'] if zone['Name'] == target_host]
            if len(target_zones) > 0:
                if len(target_zones) > 1:
                    print("WARNING: There are some hosted zone for '{}': {}".format(domain, target_zones))
                result = target_zones
                break

        return {
            'Id': result[0]['Id'],
            'Name': result[0]['Name']
        } if result != [] else dict()
    
    def _regist_to_zone(self, record: dict, zone: dict):
        '''
            recordをzoneに登録する
        '''
        confirm_text="Regist confirm: '{}' to {}]".format(record['Name'], zone)
        if self._dry:
            print(confirm_text + " Skkiped.")
        else:
            confirm = input(confirm_text + "[Y/n]")
            if 'Y' == confirm.upper():
                self._route53.change_resource_record_sets(
                    HostedZoneId=zone['Id'],
                    ChangeBatch={
                        'Comment': 'Updated by acm-validation-tool',
                        'Changes': [{
                            'Action': 'UPSERT',
                            'ResourceRecordSet': {
                                'Name': record['Name'],
                                'Type': record['Type'],
                                'TTL': 600,
                                'ResourceRecords': [
                                    { 'Value': record['Value']}
                                ]
                            }
                        }]
                    }
                )       
            else:
                print("Skipped: '{}'".format(record['Name']))
        print("[End] Domain: {}".format(record["Domain"]))

if '__main__' == __name__:
    fire.Fire(Main)
