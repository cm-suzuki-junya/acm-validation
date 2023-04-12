## 本ツールについて

ACMの検証保留中の認証レコードのエクスポートと  
そのフォーマットで出力されたCSVからのRoute 53へのレコード登録を行います。

詳細は`python3 acm-validation-tool.py --help`  
もしくは`acm-validation-tool.py`上のDocstringを参照してください。

## セットアップ

Dockerの利用は意図的に外しているため環境が必要な場合別途準備を行ってください。

```bash
% python3 --version
Python 3.11.2
% pip3 install -r requirements.txt -t lib
```

## 実行例
### エクスポート

初回作成時点ではヘッダ以外の内容についてはマネジメントコンソールからダウンロードした場合と同じです。

```bash
% python3 acm-validation-tool.py export
Domain,Name,Type,Value
example.com,_xxxxxx.example.com.,CNAME,_xxxxxxxx.tftwdmzmwn.acm-validations.aws.
mail.example.com,_xxxxxx.mail.example.com.,CNAME,_xxxxxx.tftwdmzmwn.acm-validations.aws.
```

### 登録

エクスポートのフォーマットに沿っていれば別のレコードでも登録可能です。

```bash
% python3 acm-validation-tool.py regist export.csv
[Start] Domain: example.com
Regist confirm: '_xxxxxx.example.com.' to {'Id': '/hostedzone/xxxxxx', 'Name': 'example.com.'} [Y/n]y
[End] Domain: example.com
[Start] Domain: mail.example.com
Regist confirm: '_xxxxx.mail.example.com.' to {'Id': '/hostedzone/xxxxxx', 'Name': 'example.com.'} [Y/n]y
[End] Domain: mail.example.com
```

