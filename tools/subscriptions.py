#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# subscriptions.py: list the current user's Azure subscriptions
from msrestazure.azure_active_directory import AADTokenCredentials 
from azure.mgmt.resource import SubscriptionClient

def get_token():
    import json
    # from azure.identity import InteractiveBrowserCredential
    # from azure.keyvault.secrets import SecretClient
    # VAULT_URL = "https://xtsandboxvault.vault.azure.net/"
    
    # credential = InteractiveBrowserCredential() 
    # client = SecretClient(VAULT_URL, credential=credential)
    # bundle = client.get_secret("xt-keys")
    # keys_str = bundle.value
    from xtlib.cache_client import CacheClient
    cache_client = CacheClient()
    keys_str = cache_client.get_creds("sandbox")

    keys = json.loads(keys_str)
    token = keys["outer_token"]
    return token

# 

token = get_token()
credentials = AADTokenCredentials(token)

sub_client = SubscriptionClient(credentials=credentials)
ops = sub_client.operations
subs = ops.list()
for sub in subs:
    print("sub=", sub)

