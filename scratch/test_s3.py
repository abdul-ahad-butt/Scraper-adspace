import boto3

s3_client = boto3.client(
    's3',
    endpoint_url='https://3426d738ed134463fd121ff0e9b95648.r2.cloudflarestorage.com',
    aws_access_key_id='96e7c03163dca0ac13b4d1bc42556356',
    aws_secret_access_key='3478e255d31f0c3ec71a95deaed1311ade9a09ae3bcd8b4aca6375254cf0c12d',
    region_name='auto',
    verify=False
)

try:
    import urllib3
    urllib3.disable_warnings()
    response = s3_client.list_buckets()
    print("Buckets:")
    for bucket in response['Buckets']:
        print(f" - {bucket['Name']}")
except Exception as e:
    print(f"Error: {e}")
