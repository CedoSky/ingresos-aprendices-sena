#!/usr/bin/env python
# -*- coding: utf-8 -*-

import urllib.request
import json
import sys

try:
    url = 'http://localhost:8000/api/accesos-test?limit=20'
    print(f"Testing endpoint: {url}")
    
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as response:
        status_code = response.status
        data = json.loads(response.read().decode())
        
        print(f"✅ Status Code: {status_code}")
        print(f"✅ Response Type: {type(data)}")
        print(f"✅ Keys: {list(data.keys())}")
        if 'accesos' in data:
            print(f"✅ Number of accesos: {len(data['accesos'])}")
        if 'total' in data:
            print(f"✅ Total records: {data['total']}")
        print(f"\n✅ Endpoint is working correctly!")
        
except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {str(e)}")
    sys.exit(1)
