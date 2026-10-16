"""Automated tests for Day 2 Hello MCP Server."""

import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import hello_server


def test_say_hello_with_name():
    """Verify say_hello returns personalized greeting with name."""
    result = hello_server.say_hello("Sasikala")
    assert "Hello, Sasikala!" in result
    assert "Model Context Protocol (MCP)" in result


def test_say_hello_default():
    """Verify say_hello default parameter produces greeting."""
    result = hello_server.say_hello()
    assert "Hello, World!" in result


def test_say_hello_empty_or_whitespace():
    """Verify say_hello handles empty or blank name gracefully."""
    result = hello_server.say_hello("   ")
    assert "Hello! Welcome to the Model Context Protocol (MCP)." in result
