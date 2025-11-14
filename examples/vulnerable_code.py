"""
Example vulnerable Python code for testing static analysis.

This file contains intentional security vulnerabilities for demonstration purposes.
DO NOT use this code in production!
"""

import os
import pickle
import subprocess


# SQL Injection vulnerability
def get_user_by_id(user_id):
    """Vulnerable to SQL injection."""
    query = f"SELECT * FROM users WHERE id = {user_id}"
    # This is vulnerable because user_id is not sanitized
    return execute_query(query)


# Hardcoded credentials
def connect_to_database():
    """Contains hardcoded credentials."""
    username = "admin"
    password = "password123"  # Hardcoded password - security issue
    return f"postgresql://{username}:{password}@localhost/mydb"


# Command injection
def process_file(filename):
    """Vulnerable to command injection."""
    # User input directly in shell command
    os.system(f"cat {filename}")  # Command injection risk
    subprocess.call(f"ls -la {filename}", shell=True)  # Also vulnerable


# Insecure deserialization
def load_user_data(data):
    """Insecure pickle deserialization."""
    # Pickle can execute arbitrary code
    return pickle.loads(data)  # Security risk


# Weak cryptography
def hash_password(password):
    """Uses weak hashing algorithm."""
    import hashlib
    # MD5 is cryptographically broken
    return hashlib.md5(password.encode()).hexdigest()


# Path traversal
def read_file(filename):
    """Vulnerable to path traversal."""
    # No validation of filename
    with open(f"/var/data/{filename}", "r") as f:
        return f.read()


# Insecure random
def generate_token():
    """Uses insecure random number generator."""
    import random
    # random module is not cryptographically secure
    return random.randint(100000, 999999)


# Debug mode enabled
DEBUG = True  # Should be False in production


# Unhandled exception
def divide(a, b):
    """Missing error handling."""
    return a / b  # Can raise ZeroDivisionError


# Eval usage
def calculate(expression):
    """Dangerous use of eval."""
    return eval(expression)  # Arbitrary code execution


# Assert usage
def check_admin(user):
    """Assert should not be used for security checks."""
    assert user.is_admin, "Not an admin"  # Asserts can be disabled


if __name__ == "__main__":
    # Example usage (don't run this!)
    print("This is example vulnerable code for testing.")
    print("DO NOT use in production!")
