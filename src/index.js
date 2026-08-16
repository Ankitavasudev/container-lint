/**
 * Dockerfile Linter - Web Interface
 * Interactive Dockerfile validation and linting
 */

const fs = require('fs');
const path = require('path');

class DockerfileLinter {
    constructor() {
        this.rules = [
            { name: 'FROM', check: this.checkFrom },
            { name: 'RUN', check: this.checkRun },
            { name: 'COPY', check: this.checkCopy },
            { name: 'EXPOSE', check: this.checkExpose },
            { name: 'HEALTHCHECK', check: this.checkHealthcheck },
            { name: 'USER', check: this.checkUser },
            { name: 'WORKDIR', check: this.checkWorkdir },
        ];
        this.issues = [];
    }

    checkFrom(line, lineNum) {
        const issues = [];
        if (!line.includes(':')) {
            issues.push({ line: lineNum, rule: 'FROM', message: 'FROM should use specific tag, not latest' });
        }
        if (line.includes(':latest')) {
            issues.push({ line: lineNum, rule: 'FROM', message: 'Avoid using :latest tag' });
        }
        return issues;
    }

    checkRun(line, lineNum) {
        const issues = [];
        if (line.includes('apt-get install') && !line.includes('apt-get install -y')) {
            issues.push({ line: lineNum, rule: 'RUN', message: 'Use -y flag with apt-get install' });
        }
        if (line.includes('apt-get update') && !line.includes('apt-get update &&')) {
            issues.push({ line: lineNum, rule: 'RUN', message: 'Combine apt-get update with install in single RUN' });
        }
        return issues;
    }

    checkCopy(line, lineNum) {
        const issues = [];
        if (line.includes('COPY . .') || line.includes('COPY . /')) {
            issues.push({ line: lineNum, rule: 'COPY', message: 'Use specific files instead of copying everything' });
        }
        return issues;
    }

    checkExpose(line, lineNum) {
        return [];
    }

    checkHealthcheck(line, lineNum) {
        return [];
    }

    checkUser(line, lineNum) {
        const issues = [];
        if (line.includes('USER root')) {
            issues.push({ line: lineNum, rule: 'USER', message: 'Avoid running as root' });
        }
        return issues;
    }

    checkWorkdir(line, lineNum) {
        return [];
    }

    lint(content) {
        this.issues = [];
        const lines = content.split('\n');
        
        lines.forEach((line, index) => {
            const trimmed = line.trim();
            if (trimmed === '' || trimmed.startsWith('#')) return;

            const instruction = trimmed.split(' ')[0].toUpperCase();
            const rule = this.rules.find(r => r.name === instruction);
            
            if (rule) {
                const issues = rule.check(trimmed, index + 1);
                this.issues.push(...issues);
            }
        });

        return this.issues;
    }

    generateReport() {
        const report = {
            totalIssues: this.issues.length,
            byRule: {},
            issues: this.issues
        };

        this.issues.forEach(issue => {
            if (!report.byRule[issue.rule]) {
                report.byRule[issue.rule] = 0;
            }
            report.byRule[issue.rule]++;
        });

        return report;
    }
}

function lintFile(filePath) {
    const linter = new DockerfileLinter();
    const content = fs.readFileSync(filePath, 'utf8');
    const issues = linter.lint(content);
    const report = linter.generateReport();
    
    console.log(`\nDockerfile Lint Report for: ${filePath}`);
    console.log('='.repeat(50));
    console.log(`Total issues found: ${report.totalIssues}`);
    
    if (report.totalIssues > 0) {
        console.log('\nIssues by rule:');
        Object.entries(report.byRule).forEach(([rule, count]) => {
            console.log(`  ${rule}: ${count}`);
        });
        
        console.log('\nDetailed issues:');
        report.issues.forEach(issue => {
            console.log(`  Line ${issue.line}: [${issue.rule}] ${issue.message}`);
        });
    } else {
        console.log('\nNo issues found!');
    }
    
    return report;
}

if (require.main === module) {
    const filePath = process.argv[2];
    if (!filePath) {
        console.error('Usage: node index.js <dockerfile>');
        process.exit(1);
    }
    lintFile(filePath);
}

module.exports = { DockerfileLinter, lintFile };
