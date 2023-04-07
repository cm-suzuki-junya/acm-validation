import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))

import boto3, fire
import csv

class Main:
    #TODO: 初期化処理がi/oセットになってるので分離したい
    def __init__(self, profile: str="default"):
        session = boto3.Session(profile_name=profile)
        self._acm = session.client("acm")
        self._csv_header = ["Domain", "Name", "Type", "Value"]

    def o(self):
        '''
            保留中のACMの認証レコードを出力する
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

if '__main__' == __name__:
    fire.Fire(Main)
