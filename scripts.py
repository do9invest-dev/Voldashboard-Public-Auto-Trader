"""
Development and deployment scripts.
"""

import subprocess
import sys
import os


def install_dependencies():
    """Install required dependencies."""
    print("Installing dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    print("Dependencies installed successfully!")


def run_tests():
    """Run unit tests."""
    print("Running unit tests...")
    result = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v"], 
                          capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    
    return result.returncode == 0


def run_app():
    """Run the Streamlit application."""
    print("Starting Streamlit application...")
    subprocess.check_call(["streamlit", "run", "app.py"])


def format_code():
    """Format code using black."""
    print("Formatting code with black...")
    subprocess.check_call(["black", "src/", "tests/", "app.py"])
    print("Code formatted successfully!")


def lint_code():
    """Lint code using flake8."""
    print("Linting code with flake8...")
    result = subprocess.run(["flake8", "src/", "tests/", "app.py"], 
                          capture_output=True, text=True)
    
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    
    return result.returncode == 0


def type_check():
    """Type check code using mypy."""
    print("Type checking with mypy...")
    result = subprocess.run(["mypy", "src/"], capture_output=True, text=True)
    
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    
    return result.returncode == 0


def main():
    """Main script entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts.py [install|test|run|format|lint|typecheck]")
        return
    
    command = sys.argv[1]
    
    if command == "install":
        install_dependencies()
    elif command == "test":
        success = run_tests()
        sys.exit(0 if success else 1)
    elif command == "run":
        run_app()
    elif command == "format":
        format_code()
    elif command == "lint":
        success = lint_code()
        sys.exit(0 if success else 1)
    elif command == "typecheck":
        success = type_check()
        sys.exit(0 if success else 1)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
