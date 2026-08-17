"""
Dockerfile Linter Tests
Unit tests for the Dockerfile linting functionality
"""

import unittest
import os
import tempfile


class TestDockerfileLinter(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.test_dir)
    
    def test_from_without_tag(self):
        """Test FROM without specific tag."""
        content = "FROM ubuntu\n"
        issues = self.lint_content(content)
        self.assertTrue(any("tag" in i["message"].lower() for i in issues))
    
    def test_from_with_latest(self):
        """Test FROM with :latest tag."""
        content = "FROM ubuntu:latest\n"
        issues = self.lint_content(content)
        self.assertTrue(any("latest" in i["message"].lower() for i in issues))
    
    def test_from_with_specific_tag(self):
        """Test FROM with specific tag."""
        content = "FROM ubuntu:20.04\n"
        issues = self.lint_content(content)
        self.assertFalse(any("tag" in i["message"].lower() for i in issues))
    
    def test_run_without_y_flag(self):
        """Test apt-get install without -y flag."""
        content = "RUN apt-get install curl\n"
        issues = self.lint_content(content)
        self.assertTrue(any("-y" in i["message"] for i in issues))
    
    def test_run_with_y_flag(self):
        """Test apt-get install with -y flag."""
        content = "RUN apt-get install -y curl\n"
        issues = self.lint_content(content)
        self.assertFalse(any("-y" in i["message"] for i in issues))
    
    def test_copy_all(self):
        """Test COPY . ."""
        content = "COPY . .\n"
        issues = self.lint_content(content)
        self.assertTrue(any("specific" in i["message"].lower() for i in issues))
    
    def test_copy_specific(self):
        """Test COPY with specific files."""
        content = "COPY requirements.txt .\n"
        issues = self.lint_content(content)
        self.assertFalse(any("specific" in i["message"].lower() for i in issues))
    
    def test_user_root(self):
        """Test USER root."""
        content = "USER root\n"
        issues = self.lint_content(content)
        self.assertTrue(any("root" in i["message"].lower() for i in issues))
    
    def test_comment_ignored(self):
        """Test that comments are ignored."""
        content = "# This is a comment\nFROM ubuntu:20.04\n"
        issues = self.lint_content(content)
        # Only one issue for FROM, comment should be ignored
        self.assertEqual(len([i for i in issues if i["rule"] == "FROM"]), 1)
    
    def test_empty_line_ignored(self):
        """Test that empty lines are ignored."""
        content = "\n\nFROM ubuntu:20.04\n\n"
        issues = self.lint_content(content)
        self.assertEqual(len([i for i in issues if i["rule"] == "FROM"]), 1)
    
    def lint_content(self, content):
        """Helper method to lint content."""
        issues = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            parts = line.split()
            if not parts:
                continue
            
            instruction = parts[0].upper()
            
            if instruction == 'FROM':
                if ':' not in line:
                    issues.append({
                        "line": i + 1,
                        "rule": "FROM",
                        "message": "FROM should use specific tag, not latest"
                    })
                if ':latest' in line:
                    issues.append({
                        "line": i + 1,
                        "rule": "FROM",
                        "message": "Avoid using :latest tag"
                    })
            
            elif instruction == 'RUN':
                if 'apt-get install' in line and '-y' not in line:
                    issues.append({
                        "line": i + 1,
                        "rule": "RUN",
                        "message": "Use -y flag with apt-get install"
                    })
            
            elif instruction == 'COPY':
                if 'COPY . .' in line or 'COPY . /' in line:
                    issues.append({
                        "line": i + 1,
                        "rule": "COPY",
                        "message": "Use specific files instead of copying everything"
                    })
            
            elif instruction == 'USER':
                if 'USER root' in line:
                    issues.append({
                        "line": i + 1,
                        "rule": "USER",
                        "message": "Avoid running as root"
                    })
        
        return issues


if __name__ == '__main__':
    unittest.main()
