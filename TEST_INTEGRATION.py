#!/usr/bin/env python
"""
Integration test for ControlIt refactored project
Tests: Database, Encryption, Protocol, Module imports
"""

import sys
import socket
import time
import threading

def test_database():
    print("\n[TEST 1] Database Connection & Operations")
    print("-" * 50)
    try:
        from my_connector import create_tables, register, login
        create_tables()
        print("[OK] Database tables created")

        result = register("inttest", "testpass123")
        assert result['success'], f"Register failed: {result}"
        print("[OK] User registration works")

        result = login("inttest", "testpass123")
        assert result['success'], f"Login failed: {result}"
        print("[OK] User login works")

        return True
    except Exception as e:
        print(f"[FAIL] Database test failed: {e}")
        return False

def test_encryption():
    print("\n[TEST 2] XOR Encryption/Decryption")
    print("-" * 50)
    try:
        from crypto import encrypt, decrypt

        messages = [
            "Hello World",
            "CMD|SCREENSHOT|",
            "OK|response_data_here",
            "Admin Command Test 12345"
        ]

        for msg in messages:
            encrypted = encrypt(msg)
            decrypted = decrypt(encrypted)
            assert decrypted == msg, f"Mismatch: {msg} != {decrypted}"

        print(f"[OK] Successfully encrypted/decrypted {len(messages)} messages")
        return True
    except Exception as e:
        print(f"[FAIL] Encryption test failed: {e}")
        return False

def test_protocol():
    print("\n[TEST 3] Pipe-Delimited Protocol")
    print("-" * 50)
    try:
        from net_utils import send_msg, recv_msg

        def server_thread():
            s = socket.socket()
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("127.0.0.1", 10001))
            s.listen(1)
            c, _ = s.accept()

            # Receive client command
            msg = recv_msg(c)
            assert msg[0] == "CMD", f"Expected CMD, got {msg[0]}"
            assert msg[1] == "SYSINFO", f"Expected SYSINFO, got {msg[1]}"
            print("[OK] Server received: CMD|SYSINFO|")

            # Send response
            send_msg(c, ["OK", "System info response"])
            c.close()
            s.close()

        # Start server in background
        server = threading.Thread(target=server_thread, daemon=True)
        server.start()
        time.sleep(0.3)

        # Client connects and sends command
        c = socket.socket()
        c.connect(("127.0.0.1", 10001))
        send_msg(c, "CMD|SYSINFO|")
        resp = recv_msg(c)
        assert resp[0] == "OK", f"Expected OK, got {resp[0]}"
        print(f"[OK] Client received: OK|{resp[1][:20]}...")
        c.close()

        server.join(timeout=1)
        return True
    except Exception as e:
        print(f"[FAIL] Protocol test failed: {e}")
        return False

def test_imports():
    print("\n[TEST 4] Module Imports")
    print("-" * 50)
    try:
        modules = [
            "my_connector",
            "crypto",
            "net_utils",
            "launcher",
            "login_page",
            "main_menu",
            "agent_gui"
        ]

        for mod in modules:
            __import__(mod)
            print(f"[OK] {mod}")

        return True
    except Exception as e:
        print(f"[FAIL] Import test failed: {e}")
        return False

def test_ui():
    print("\n[TEST 5] UI Module Syntax")
    print("-" * 50)
    try:
        import tkinter as tk
        import launcher
        import login_page

        # Just verify the classes exist and have the right methods
        assert hasattr(launcher, 'ControlItLauncher')
        assert hasattr(login_page, 'LoginApp')
        print("[OK] launcher.ControlItLauncher exists")
        print("[OK] login_page.LoginApp exists")

        return True
    except Exception as e:
        print(f"[FAIL] UI test failed: {e}")
        return False

def main():
    print("\n" + "=" * 50)
    print("  ControlIt Integration Test Suite")
    print("=" * 50)

    tests = [
        ("Database", test_database),
        ("Encryption", test_encryption),
        ("Protocol", test_protocol),
        ("Imports", test_imports),
        ("UI", test_ui),
    ]

    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"Test {name} crashed: {e}")
            results[name] = False

    print("\n" + "=" * 50)
    print("  TEST RESULTS")
    print("=" * 50)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = "PASS" if result else "FAIL"
        symbol = "[OK]" if result else "[X]"
        print(f"  {symbol} {name:20} [{status}]")

    print("=" * 50)
    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\nALL TESTS PASSED! Project is ready for use.\n")
        return 0
    else:
        print(f"\n{total - passed} test(s) failed.\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
