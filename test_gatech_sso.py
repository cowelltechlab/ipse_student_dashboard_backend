#!/usr/bin/env python3
"""
Simple test script to verify Georgia Tech SSO integration.
This script tests the basic functionality without requiring a full application server.
"""

import sys
import os

# Add the application directory to Python path
sys.path.insert(0, os.path.abspath('.'))

def test_saml_imports():
    """Test if SAML modules can be imported successfully."""
    try:
        from application.features.auth.gatech_saml import (
            get_saml_settings, 
            GT_ATTRIBUTE_MAPPING,
            GT_IDP_METADATA_URL
        )
        print("[PASS] SAML module imports successful")
        return True
    except ImportError as e:
        print(f"[FAIL] SAML module import failed: {e}")
        return False

def test_saml_settings():
    """Test SAML settings generation."""
    try:
        from application.features.auth.gatech_saml import get_saml_settings
        
        settings = get_saml_settings()
        
        # Verify required settings are present
        required_keys = ['sp', 'idp']
        for key in required_keys:
            if key not in settings:
                print(f"[FAIL] Missing required setting: {key}")
                return False
        
        # Verify IdP configuration
        idp = settings['idp']
        if not idp.get('entityId'):
            print("[FAIL] Missing IdP entityId")
            return False
        
        if not idp.get('x509cert'):
            print("[FAIL] Missing IdP certificate")
            return False
            
        print("[PASS] SAML settings generation successful")
        print(f"  - IdP Entity ID: {idp['entityId']}")
        print(f"  - IdP SSO URL: {idp['singleSignOnService']['url']}")
        print(f"  - SP Entity ID: {settings['sp']['entityId']}")
        return True
        
    except Exception as e:
        print(f"[FAIL] SAML settings test failed: {e}")
        return False

def test_attribute_mapping():
    """Test attribute mapping configuration."""
    try:
        from application.features.auth.gatech_saml import GT_ATTRIBUTE_MAPPING
        
        required_attributes = [
            "eduPersonPrincipalName",
            "uid", 
            "givenname",
            "sn"
        ]
        
        for attr in required_attributes:
            if attr not in GT_ATTRIBUTE_MAPPING:
                print(f"[FAIL] Missing attribute mapping for: {attr}")
                return False
        
        print("[PASS] Attribute mapping configuration successful")
        for attr, oid in GT_ATTRIBUTE_MAPPING.items():
            print(f"  - {attr}: {oid}")
        return True
        
    except Exception as e:
        print(f"[FAIL] Attribute mapping test failed: {e}")
        return False

def test_routes_integration():
    """Test if auth routes can load with SAML integration."""
    try:
        # This will test if the routes file can be imported with SAML functions
        from application.features.auth.routes import router
        print("[PASS] Routes integration successful")
        return True
    except Exception as e:
        print(f"[FAIL] Routes integration failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Georgia Tech SSO Integration Tests")
    print("=" * 40)
    
    tests = [
        test_saml_imports,
        test_saml_settings, 
        test_attribute_mapping,
        test_routes_integration
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 40)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("[PASS] All tests passed! Georgia Tech SSO integration appears to be working correctly.")
        print("\nNext steps:")
        print("1. Start your FastAPI application")
        print("2. Access /auth/login/gatech to get the SSO URL")
        print("3. Test the complete login flow with Georgia Tech credentials")
    else:
        print("[FAIL] Some tests failed. Please check the configuration.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())