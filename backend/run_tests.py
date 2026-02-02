#!/usr/bin/env python3
import subprocess
import sys
import os
import argparse
from pathlib import Path


def install_test_dependencies():
    print("📦 Installing test dependencies...")
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements-test.txt"
        ], check=True)
        print("✅ Test dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install test dependencies: {e}")
        return False


def run_tests(test_type="all", coverage=False, verbose=False, markers=None, parallel=False):
    
    cmd = [sys.executable, "-m", "pytest"]
    
    if test_type == "unit":
        cmd.extend(["tests/unit/"])
        cmd.extend(["-m", "unit"])
    elif test_type == "integration":
        cmd.extend(["tests/integration/"])
        cmd.extend(["-m", "integration"])
    elif test_type == "api":
        cmd.extend(["-m", "api"])
    else:
        cmd.extend(["tests/"])
    
    if markers:
        for marker in markers:
            cmd.extend(["-m", marker])
    
    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")
    
    if coverage:
        cmd.extend([
            "--cov=.",
            "--cov-report=term-missing:skip-covered"
        ])
    
    if parallel:
        cmd.extend(["-n", "auto"])
    
    print(f"🔄 Running {test_type} tests...")
    
    try:
        result = subprocess.run(cmd, check=False)
        
        if result.returncode == 0:
            print("✅ All tests passed!")
        else:
            print(f"❌ Tests failed with return code: {result.returncode}")
            
        return result.returncode == 0
        
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        return False
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False


def run_linting():
    print("🔍 Running code linting...")
    
    lint_commands = [
        ([sys.executable, "-m", "flake8", ".", "--max-line-length=120"], "Flake8"),
        ([sys.executable, "-m", "black", "--check", "."], "Black"),
        ([sys.executable, "-m", "isort", "--check-only", "."], "isort"),
    ]
    
    all_passed = True
    
    for cmd, tool in lint_commands:
        try:
            result = subprocess.run(cmd, check=False, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ {tool} passed")
            else:
                print(f"❌ {tool} failed:")
                if result.stdout:
                    print(result.stdout)
                if result.stderr:
                    print(result.stderr)
                all_passed = False
        except FileNotFoundError:
            print(f"⚠️ {tool} not installed, skipping...")
    
    return all_passed


def run_security_scan():
    print("🔐 Running security scan...")
    
    security_commands = [
        ([sys.executable, "-m", "bandit", "-r", "."], "Bandit"),
        ([sys.executable, "-m", "safety", "check"], "Safety"),
    ]
    
    for cmd, tool in security_commands:
        try:
            result = subprocess.run(cmd, check=False)
            if result.returncode == 0:
                print(f"✅ {tool} scan passed")
            else:
                print(f"⚠️ {tool} found issues")
        except FileNotFoundError:
            print(f"⚠️ {tool} not installed, skipping...")


def main():
    parser = argparse.ArgumentParser(description="Financial Agent System Test Runner")
    
    parser.add_argument(
        "--type", "-t",
        choices=["all", "unit", "integration", "api"],
        default="all",
        help="Type of tests to run"
    )
    
    parser.add_argument(
        "--coverage", "-c",
        action="store_true",
        help="Enable coverage reporting"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true", 
        help="Verbose output"
    )
    
    parser.add_argument(
        "--parallel", "-p",
        action="store_true",
        help="Run tests in parallel"
    )
    
    parser.add_argument(
        "--markers", "-m",
        nargs="+",
        help="Additional pytest markers to filter tests"
    )
    
    parser.add_argument(
        "--install-deps", "-i",
        action="store_true",
        help="Install test dependencies before running"
    )
    
    parser.add_argument(
        "--lint", "-l",
        action="store_true", 
        help="Run linting checks"
    )
    
    parser.add_argument(
        "--security", "-s",
        action="store_true",
        help="Run security scans"
    )
    
    parser.add_argument(
        "--all-checks", "-a",
        action="store_true",
        help="Run tests, linting, and security scans"
    )
    
    args = parser.parse_args()
    
    success = True
    
    if args.install_deps:
        if not install_test_dependencies():
            return 1
    
    if args.lint or args.all_checks:
        if not run_linting():
            success = False
    
    if not args.lint and not args.security:
        if not run_tests(
            test_type=args.type,
            coverage=args.coverage,
            verbose=args.verbose,
            markers=args.markers,
            parallel=args.parallel
        ):
            success = False
    
    if args.security or args.all_checks:
        run_security_scan()
    
    if success:
        print("\n🎉 All checks completed successfully!")
        return 0
    else:
        print("\n💥 Some checks failed!")
        return 1


if __name__ == "__main__":
    exit(main())