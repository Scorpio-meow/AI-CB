#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全掃描工具 - 掃描代碼中的敏感信息和安全漏洞
"""

import re
import os
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

class SecurityScanner:
    """安全掃描器"""
    
    # 敏感信息模式
    PATTERNS = {
        'hardcoded_password': {
            'pattern': r'(?i)(password|passwd|pwd)\s*[:=]\s*["\']([^"\'\s]{8,})["\']',
            'severity': 'HIGH',
            'description': '硬編碼密碼'
        },
        'api_key': {
            'pattern': r'(?i)(api[_-]?key|apikey)\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?',
            'severity': 'HIGH',
            'description': 'API Key 可能洩露'
        },
        'secret_key': {
            'pattern': r'(?i)(secret[_-]?key|token)\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?',
            'severity': 'HIGH',
            'description': '密鑰可能洩露'
        },
        'private_key': {
            'pattern': r'-----BEGIN.*PRIVATE KEY-----',
            'severity': 'CRITICAL',
            'description': '私鑰文件'
        },
        'connection_string': {
            'pattern': r'(?i)(connection[_-]?string|database[_-]?url)\s*[:=]\s*["\']?([^"\'\s]+@[^"\'\s]+)["\']?',
            'severity': 'HIGH',
            'description': '數據庫連接字符串包含密碼'
        },
        'ip_address': {
            'pattern': r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
            'severity': 'LOW',
            'description': '硬編碼 IP 地址'
        },
        'sql_injection_risk': {
            'pattern': r'(?i)(execute|executemany|raw)\s*\([^)]*%[sd]',
            'severity': 'MEDIUM',
            'description': '可能存在 SQL 注入風險'
        },
        'eval_usage': {
            'pattern': r'\b(eval|exec)\s*\(',
            'severity': 'CRITICAL',
            'description': '使用 eval/exec（代碼注入風險）'
        },
        'shell_injection': {
            'pattern': r'(os\.system|subprocess\.[^(]+)\([^)]*shell\s*=\s*True',
            'severity': 'CRITICAL',
            'description': '命令注入風險'
        },
    }
    
    # 排除的目錄和文件
    EXCLUDE_DIRS = {
        'node_modules', '__pycache__', '.git', 'venv', 'CBvenv', 
        'build', 'dist', '.vscode', 'logs', 'data'
    }
    
    EXCLUDE_FILES = {
        '.pyc', '.min.js', '.map', '.lock', 'package-lock.json'
    }
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.results = []
        
    def should_scan_file(self, file_path: Path) -> bool:
        """判斷是否應該掃描文件"""
        # 排除特定目錄
        for exclude_dir in self.EXCLUDE_DIRS:
            if exclude_dir in file_path.parts:
                return False
        
        # 排除特定文件類型
        if any(file_path.name.endswith(ext) for ext in self.EXCLUDE_FILES):
            return False
        
        # 只掃描代碼文件
        code_extensions = {'.py', '.js', '.jsx', '.ts', '.tsx', '.env', '.conf', '.config', '.yaml', '.yml'}
        return file_path.suffix in code_extensions
    
    def scan_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """掃描單個文件"""
        findings = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
            
            for pattern_name, pattern_info in self.PATTERNS.items():
                matches = re.finditer(pattern_info['pattern'], content, re.MULTILINE)
                
                for match in matches:
                    # 找到匹配的行號
                    line_num = content[:match.start()].count('\n') + 1
                    
                    # 獲取上下文
                    context_start = max(0, line_num - 2)
                    context_end = min(len(lines), line_num + 2)
                    context = '\n'.join(lines[context_start:context_end])
                    
                    findings.append({
                        'file': str(file_path.relative_to(self.project_root)),
                        'line': line_num,
                        'pattern': pattern_name,
                        'severity': pattern_info['severity'],
                        'description': pattern_info['description'],
                        'matched_text': match.group(0)[:100],  # 限制長度
                        'context': context[:200]  # 限制上下文長度
                    })
        
        except Exception as e:
            # 使用 ASCII 安全的輸出
            print(f"[ERROR] Failed to scan file {file_path}: {e}")
        
        return findings
    
    def scan_project(self) -> List[Dict[str, Any]]:
        """掃描整個專案"""
        print("\n" + "=" * 80)
        print("Security Scan - Analyzing Project")
        print(f"Project: {self.project_root}")
        print("=" * 80)
        
        all_findings = []
        scanned_count = 0
        
        for root, dirs, files in os.walk(self.project_root):
            # 移除排除的目錄
            dirs[:] = [d for d in dirs if d not in self.EXCLUDE_DIRS]
            
            for file in files:
                file_path = Path(root) / file
                
                if self.should_scan_file(file_path):
                    scanned_count += 1
                    findings = self.scan_file(file_path)
                    all_findings.extend(findings)
        
        print(f"\nScan Complete: {scanned_count} files scanned")
        print(f"Issues Found: {len(all_findings)}\n")
        
        return all_findings
    
    def generate_report(self, findings: List[Dict[str, Any]]) -> str:
        """生成掃描報告"""
        # 按嚴重程度分類
        by_severity = {
            'CRITICAL': [],
            'HIGH': [],
            'MEDIUM': [],
            'LOW': []
        }
        
        for finding in findings:
            severity = finding['severity']
            by_severity[severity].append(finding)
        
        # 生成報告
        report = []
        report.append("=" * 80)
        report.append("Security Scan Report")
        report.append(f"Scan Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 80)
        report.append("")
        
        # 摘要
        report.append("Issue Summary:")
        report.append(f"  CRITICAL: {len(by_severity['CRITICAL'])}")
        report.append(f"  HIGH: {len(by_severity['HIGH'])}")
        report.append(f"  MEDIUM: {len(by_severity['MEDIUM'])}")
        report.append(f"  LOW: {len(by_severity['LOW'])}")
        report.append("")
        
        # 詳細問題列表
        for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            if by_severity[severity]:
                report.append("")
                report.append(f"{'=' * 80}")
                report.append(f"{severity} Risk Issues")
                report.append(f"{'=' * 80}")
                
                for idx, finding in enumerate(by_severity[severity], 1):
                    report.append(f"\n{idx}. {finding['description']}")
                    report.append(f"   File: {finding['file']}:{finding['line']}")
                    report.append(f"   Pattern: {finding['pattern']}")
                    if finding.get('matched_text'):
                        report.append(f"   Match: {finding['matched_text']}")
                    report.append("")
        
        return '\n'.join(report)
    
    def save_report(self, findings: List[Dict[str, Any]], output_file: str = None):
        """保存報告"""
        if output_file is None:
            output_file = self.project_root / 'security_scan_report.txt'
        
        report_text = self.generate_report(findings)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        print(f"\nReport saved to: {output_file}")
        
        # 同時保存 JSON 格式
        json_file = str(output_file).replace('.txt', '.json')
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(findings, f, indent=2, ensure_ascii=False)
        
        print(f"JSON report saved to: {json_file}\n")

def main():
    """主函數"""
    # 獲取專案根目錄
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    
    scanner = SecurityScanner(project_root)
    findings = scanner.scan_project()
    
    # 生成並顯示報告
    report = scanner.generate_report(findings)
    print(report)
    
    # 保存報告
    scanner.save_report(findings)
    
    # 返回錯誤代碼
    critical_count = sum(1 for f in findings if f['severity'] == 'CRITICAL')
    high_count = sum(1 for f in findings if f['severity'] == 'HIGH')
    
    if critical_count > 0 or high_count > 0:
        print("\n[WARNING] Critical or high-risk issues found!")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())
