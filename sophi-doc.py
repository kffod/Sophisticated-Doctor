import os
import requests
import argparse
import sys
import time
import itertools
import fnmatch
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import ast
import subprocess
from pathlib import Path

# --- Configuration ---
CONFIG_FILE = os.path.expanduser("~/.sophisticated_doctor_config.json")
CACHE_DIR = os.path.expanduser("~/.sophisticated_doctor_cache")

# AI Providers Configuration
AI_PROVIDERS = {
    "gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent",
        "env_key": "GEMINI_API_KEY",
        "max_tokens": 100000
    },
    "openai": {
        "url": "https://api.openai.com/v1/chat/completions",
        "env_key": "OPENAI_API_KEY",
        "max_tokens": 120000
    },
    "anthropic": {
        "url": "https://api.anthropic.com/v1/messages",
        "env_key": "ANTHROPIC_API_KEY",
        "max_tokens": 100000
    }
}

# Add directories and file extensions to ignore during analysis
DEFAULT_IGNORE_DIRS = {'.git', '__pycache__', 'node_modules', '.vscode', '.idea', 'venv', 'env', 'dist', 'build'}
DEFAULT_IGNORE_EXTENSIONS = {'.pyc', '.pyo', '.o', '.so', '.dll', '.exe', '.DS_Store', '.log', '.tmp'}

# File size limits (in bytes)
DEFAULT_MAX_FILE_SIZE = 1024 * 1024  # 1MB
DEFAULT_MAX_TOTAL_SIZE = 10 * 1024 * 1024  # 10MB

def print_title():
    """Prints the ASCII art title for the tool."""
    art = r"""
    ███████╗ ██████╗ ██████╗ ██╗  ██╗██╗███████╗████████╗██╗ ██████╗ █████╗ ████████╗███████╗██████╗ 
    ██╔════╝██╔═══██╗██╔══██╗██║  ██║██║██╔════╝╚══██╔══╝██║██╔════╝██╔══██╗╚══██╔══╝██╔════╝██╔══██╗
    ███████╗██║   ██║██████╔╝███████║██║███████╗   ██║   ██║██║     ███████║   ██║   █████╗  ██║  ██║
    ╚════██║██║   ██║██╔═══╝ ██╔══██║██║╚════██║   ██║   ██║██║     ██╔══██║   ██║   ██╔══╝  ██║  ██║
    ███████║╚██████╔╝██║     ██║  ██║██║███████║   ██║   ██║╚██████╗██║  ██║   ██║   ███████╗██████╔╝
    ╚══════╝ ╚═════╝ ╚═╝     ╚═╝  ╚═╝╚═╝╚══════╝   ╚═╝   ╚═╝ ╚═════╝╚═╝  ╚═╝   ╚═╝   ╚══════╝╚═════╝ 
    """
    print(f"\033[95m{art}\033[0m")
    print(f"\033[96m                           Enhanced Edition with AI Provider Support\033[0m")
    print("-" * 80)

def load_config():
    """Load configuration from file."""
    default_config = {
        "default_provider": "gemini",
        "max_file_size": DEFAULT_MAX_FILE_SIZE,
        "max_total_size": DEFAULT_MAX_TOTAL_SIZE,
        "cache_enabled": True,
        "cache_duration_hours": 24,
        "enable_static_analysis": True
    }
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                # Merge with defaults
                default_config.update(config)
        except Exception as e:
            print(f"\033[93mWarning: Could not load config file: {e}\033[0m")
    
    return default_config

def save_config(config):
    """Save configuration to file."""
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"\033[93mWarning: Could not save config file: {e}\033[0m")

def get_api_key(provider: str):
    """Fetches the API key for the specified provider from environment variables."""
    if provider not in AI_PROVIDERS:
        print(f"\033[91mError: Unknown provider '{provider}'. Available providers: {', '.join(AI_PROVIDERS.keys())}\033[0m")
        sys.exit(1)
    
    api_key = os.environ.get(AI_PROVIDERS[provider]["env_key"])
    if not api_key:
        print(f"\033[91mError: {AI_PROVIDERS[provider]['env_key']} environment variable not set for {provider}.\033[0m")
        print(f"Please set it by running:")
        print(f"\033[93mexport {AI_PROVIDERS[provider]['env_key']}='YOUR_API_KEY_HERE'\033[0m")
        sys.exit(1)
    return api_key

def create_progress_bar(total: int, prefix: str = "Progress"):
    """Create a simple progress bar."""
    class ProgressBar:
        def __init__(self, total, prefix):
            self.total = total
            self.current = 0
            self.prefix = prefix
            
        def update(self, increment=1):
            self.current += increment
            percent = (self.current / self.total) * 100
            filled = int(percent // 2)
            bar = "█" * filled + "░" * (50 - filled)
            print(f"\r\033[94m{self.prefix}: [{bar}] {percent:.1f}% ({self.current}/{self.total})\033[0m", end="", flush=True)
            
        def finish(self):
            print()  # New line after completion
    
    return ProgressBar(total, prefix)

def perform_static_analysis(file_path: str, content: str) -> Dict[str, any]:
    """Perform basic static analysis on the file."""
    analysis = {
        "file_path": file_path,
        "lines_of_code": len(content.splitlines()),
        "size_bytes": len(content.encode('utf-8')),
        "issues": []
    }
    
    # Python-specific analysis
    if file_path.endswith('.py'):
        try:
            tree = ast.parse(content)
            
            # Count functions and classes
            functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
            classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
            
            analysis.update({
                "functions": len(functions),
                "classes": len(classes),
                "complexity_score": len(functions) + len(classes) * 2
            })
            
            # Basic issue detection
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if len(node.args.args) > 5:
                        analysis["issues"].append(f"Function '{node.name}' has {len(node.args.args)} parameters (consider reducing)")
                    if not ast.get_docstring(node):
                        analysis["issues"].append(f"Function '{node.name}' lacks documentation")
                        
        except SyntaxError as e:
            analysis["issues"].append(f"Syntax error: {e}")
        except Exception as e:
            analysis["issues"].append(f"Analysis error: {e}")
    
    # JavaScript/TypeScript analysis
    elif file_path.endswith(('.js', '.ts', '.jsx', '.tsx')):
        # Simple pattern matching for common issues
        if 'console.log(' in content:
            analysis["issues"].append("Contains console.log statements (remove for production)")
        if 'var ' in content:
            analysis["issues"].append("Uses 'var' declarations (consider 'let' or 'const')")
        if content.count('function') > 10:
            analysis["issues"].append(f"High function count ({content.count('function')}) - consider refactoring")
    
    return analysis

def calculate_project_hash(project_path: str, ignore_patterns: List[str]) -> str:
    """Calculate a hash of the project structure and content for caching."""
    hasher = hashlib.sha256()
    
    for root, dirs, files in os.walk(project_path):
        # Apply ignore patterns
        all_ignored_dirs = DEFAULT_IGNORE_DIRS.union(
            {d for p in ignore_patterns for d in fnmatch.filter(dirs, p)}
        )
        dirs[:] = [d for d in dirs if d not in all_ignored_dirs]
        
        for file in sorted(files):
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, project_path)
            file_extension = os.path.splitext(file)[1]
            
            if file_extension in DEFAULT_IGNORE_EXTENSIONS:
                continue
            if any(fnmatch.fnmatch(relative_path, pattern) for pattern in ignore_patterns):
                continue
                
            # Add file path and modification time to hash
            hasher.update(relative_path.encode())
            try:
                stat = os.stat(file_path)
                hasher.update(str(stat.st_mtime).encode())
                hasher.update(str(stat.st_size).encode())
            except Exception:
                pass
    
    return hasher.hexdigest()

def get_cached_result(cache_key: str, max_age_hours: int = 24) -> Optional[str]:
    """Retrieve cached analysis result if it exists and is not expired."""
    if not os.path.exists(CACHE_DIR):
        return None
        
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
    if not os.path.exists(cache_file):
        return None
        
    try:
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
            
        created_time = datetime.fromisoformat(cache_data["created"])
        if datetime.now() - created_time > timedelta(hours=max_age_hours):
            os.remove(cache_file)  # Remove expired cache
            return None
            
        return cache_data["result"]
    except Exception:
        return None

def save_cached_result(cache_key: str, result: str):
    """Save analysis result to cache."""
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
        
        cache_data = {
            "created": datetime.now().isoformat(),
            "result": result
        }
        
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f)
    except Exception as e:
        print(f"\033[93mWarning: Could not save to cache: {e}\033[0m")

def read_project_files(project_path: str, custom_ignore_patterns: List[str] = None, 
                      verbose: bool = False, max_file_size: int = DEFAULT_MAX_FILE_SIZE,
                      max_total_size: int = DEFAULT_MAX_TOTAL_SIZE,
                      enable_static_analysis: bool = True) -> Tuple[str, List[Dict], Dict]:
    """
    Reads all files in a project directory with enhanced features.
    Returns: (content_string, static_analysis_results, stats)
    """
    all_files_content = []
    static_analysis_results = []
    project_path = os.path.abspath(project_path)
    ignore_patterns = custom_ignore_patterns or []
    
    if not os.path.isdir(project_path):
        print(f"\033[91mError: The path '{project_path}' is not a valid directory.\033[0m")
        sys.exit(1)

    print(f"\033[94mAnalyzing project at: {project_path}\033[0m")

    # First pass: count files for progress bar
    file_count = 0
    total_size = 0
    skipped_files = []
    
    for root, dirs, files in os.walk(project_path, topdown=True):
        all_ignored_dirs = DEFAULT_IGNORE_DIRS.union(
            {d for p in ignore_patterns for d in fnmatch.filter(dirs, p)}
        )
        dirs[:] = [d for d in dirs if d not in all_ignored_dirs]
        
        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, project_path)
            file_extension = os.path.splitext(file)[1]
            
            if file_extension in DEFAULT_IGNORE_EXTENSIONS:
                continue
            if any(fnmatch.fnmatch(relative_path, pattern) for pattern in ignore_patterns):
                continue
                
            try:
                file_size = os.path.getsize(file_path)
                if file_size > max_file_size:
                    skipped_files.append(f"{relative_path} (size: {file_size/1024:.1f}KB)")
                    continue
                if total_size + file_size > max_total_size:
                    skipped_files.append(f"{relative_path} (total size limit reached)")
                    continue
                    
                file_count += 1
                total_size += file_size
            except Exception:
                continue

    if file_count == 0:
        print("\033[91mError: No readable files found in the specified directory.\033[0m")
        sys.exit(1)

    # Create progress bar
    progress = create_progress_bar(file_count, "Reading files")
    
    # Second pass: actually read files
    processed_files = 0
    for root, dirs, files in os.walk(project_path, topdown=True):
        all_ignored_dirs = DEFAULT_IGNORE_DIRS.union(
            {d for p in ignore_patterns for d in fnmatch.filter(dirs, p)}
        )
        dirs[:] = [d for d in dirs if d not in all_ignored_dirs]

        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, project_path)
            file_extension = os.path.splitext(file)[1]

            if file_extension in DEFAULT_IGNORE_EXTENSIONS:
                continue
            if any(fnmatch.fnmatch(relative_path, pattern) for pattern in ignore_patterns):
                continue
            
            try:
                file_size = os.path.getsize(file_path)
                if file_size > max_file_size or relative_path in [f.split(' (')[0] for f in skipped_files]:
                    continue
            except Exception:
                continue
            
            if verbose:
                print(f"\n\033[90m  + Reading: {relative_path}\033[0m")

            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    formatted_content = f"--- Filename: {relative_path} ---\n{content}\n"
                    all_files_content.append(formatted_content)
                    
                    # Perform static analysis if enabled
                    if enable_static_analysis:
                        analysis = perform_static_analysis(relative_path, content)
                        static_analysis_results.append(analysis)
                        
                processed_files += 1
                progress.update()
                
            except Exception as e:
                print(f"\n\033[93mWarning: Could not read file {file_path}: {e}\033[0m")

    progress.finish()
    
    # Print summary statistics
    stats = {
        "total_files": processed_files,
        "total_size_kb": total_size / 1024,
        "skipped_files": skipped_files
    }
    
    if skipped_files:
        print(f"\033[93mSkipped {len(skipped_files)} files due to size limits:\033[0m")
        for skipped in skipped_files[:5]:  # Show first 5
            print(f"  - {skipped}")
        if len(skipped_files) > 5:
            print(f"  ... and {len(skipped_files) - 5} more")
    
    print(f"\033[92mProcessed {processed_files} files ({total_size/1024:.1f}KB total)\033[0m")
        
    return "\n".join(all_files_content), static_analysis_results, stats

def format_static_analysis_summary(analysis_results: List[Dict]) -> str:
    """Format static analysis results into a readable summary."""
    if not analysis_results:
        return ""
    
    total_lines = sum(r["lines_of_code"] for r in analysis_results)
    total_issues = sum(len(r["issues"]) for r in analysis_results)
    
    summary = f"\n### 📊 Static Analysis Summary\n"
    summary += f"- **Total Lines of Code**: {total_lines:,}\n"
    summary += f"- **Files Analyzed**: {len(analysis_results)}\n"
    summary += f"- **Issues Found**: {total_issues}\n\n"
    
    if total_issues > 0:
        summary += "**Top Issues Found:**\n"
        all_issues = []
        for result in analysis_results:
            for issue in result["issues"]:
                all_issues.append(f"- {result['file_path']}: {issue}")
        
        # Show top 10 issues
        for issue in all_issues[:10]:
            summary += f"{issue}\n"
        
        if len(all_issues) > 10:
            summary += f"... and {len(all_issues) - 10} more issues\n"
    
    return summary

def get_diagnosis(api_key: str, provider: str, project_type: str, project_content: str, 
                 static_analysis_summary: str = "") -> str:
    """Calls the specified AI provider to get the project analysis."""
    system_prompt = """You are an expert code reviewer and software architect, acting as an "AI Project Doctor". Your tone is helpful, constructive, and easy to understand. Analyze the following project files and structure to identify potential issues. Look for common mistakes, missing files, bad practices, and areas for improvement.

Provide a simple, clear, and actionable summary of your findings. Format your response in Markdown, ready for terminal output. Use emojis to make the categories more engaging.

Categorize your feedback into three main sections:
- ### 🚨 Critical Issues: Things that are likely broken, represent security vulnerabilities, or will cause errors.
- ### 🤔 Things You Might Be Forgetting: Suggestions for missing best practices, files, or features (e.g., 'You might be forgetting a README.md file to explain your project' or 'You are missing error handling in your main function.').
- ### ✨ Suggestions for Improvement: Ideas for refactoring, better code style, performance optimizations, or improving maintainability.

Start with a brief, one-sentence summary of the project's overall health before diving into the categories."""
    
    user_query = f"Project Type: {project_type}\n\n{static_analysis_summary}Project Files & Content:\n---\n{project_content}"

    # Provider-specific API calls
    if provider == "gemini":
        return call_gemini_api(api_key, system_prompt, user_query)
    elif provider == "openai":
        return call_openai_api(api_key, system_prompt, user_query)
    elif provider == "anthropic":
        return call_anthropic_api(api_key, system_prompt, user_query)
    else:
        return f"\033[91mError: Provider {provider} not implemented yet.\033[0m"

def call_gemini_api(api_key: str, system_prompt: str, user_query: str) -> str:
    """Call Gemini API."""
    payload = {
        "contents": [{"parts": [{"text": user_query}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
    }
    
    headers = {'Content-Type': 'application/json'}
    params = {'key': api_key}
    
    try:
        response = requests.post(AI_PROVIDERS["gemini"]["url"], headers=headers, params=params, json=payload)
        response.raise_for_status()
        result = response.json()
        
        candidate = result.get("candidates", [{}])[0]
        analysis_text = candidate.get("content", {}).get("parts", [{}])[0].get("text")
        
        return analysis_text or f"\033[91mError: Invalid response from Gemini API.\033[0m"
    except Exception as e:
        return f"\033[91mGemini API request failed: {e}\033[0m"

def call_openai_api(api_key: str, system_prompt: str, user_query: str) -> str:
    """Call OpenAI API."""
    payload = {
        "model": "gpt-4-turbo-preview",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query}
        ],
        "max_tokens": 4000
    }
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    try:
        response = requests.post(AI_PROVIDERS["openai"]["url"], headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        return f"\033[91mOpenAI API request failed: {e}\033[0m"

def call_anthropic_api(api_key: str, system_prompt: str, user_query: str) -> str:
    """Call Anthropic Claude API."""
    payload = {
        "model": "claude-3-sonnet-20240229",
        "max_tokens": 4000,
        "system": system_prompt,
        "messages": [
            {"role": "user", "content": user_query}
        ]
    }
    
    headers = {
        'Content-Type': 'application/json',
        'x-api-key': api_key,
        'anthropic-version': '2023-06-01'
    }
    
    try:
        response = requests.post(AI_PROVIDERS["anthropic"]["url"], headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        
        return result["content"][0]["text"]
    except Exception as e:
        return f"\033[91mAnthropic API request failed: {e}\033[0m"

def show_loading_animation(duration: float = 3.0):
    """Show a loading animation while processing."""
    spinner = itertools.cycle(["⢿", "⣻", "⣽", "⣾", "⣷", "⣯", "⣟", "⡿"])
    start_time = time.time()
    
    sys.stdout.write("\033[94mThe AI doctor is examining your project... \033[0m")
    sys.stdout.flush()
    
    while time.time() - start_time < duration:
        sys.stdout.write(f"\r\033[94mThe AI doctor is examining your project... {next(spinner)}\033[0m")
        sys.stdout.flush()
        time.sleep(0.1)
    
    sys.stdout.write("\r" + " " * 50 + "\r")  # Clear the line
    sys.stdout.flush()

def main():
    """Main function to parse arguments and run the analysis."""
    print_title()
    config = load_config()
    
    parser = argparse.ArgumentParser(
        description="Enhanced AI Project Doctor - A CLI tool to analyze your projects using multiple AI providers.",
        epilog="Example: python enhanced_doctor.py ./my-app -t \"Node.js API\" --provider openai --ignore \"docs\" -o report.md"
    )
    parser.add_argument("path", help="The path to the project directory you want to analyze.")
    parser.add_argument("-t", "--type", required=True, help="A short description of the project type (e.g., 'Python Flask API', 'React component').")
    parser.add_argument("-p", "--provider", default=config["default_provider"], 
                       choices=AI_PROVIDERS.keys(), help=f"AI provider to use (default: {config['default_provider']})")
    parser.add_argument("-o", "--output", help="Path to save the report as a Markdown file (e.g., report.md).")
    parser.add_argument("-i", "--ignore", action="append", help="A file or directory pattern to ignore (e.g., 'docs', '*.log'). Can be used multiple times.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print the names of the files being analyzed.")
    parser.add_argument("-q", "--quiet", action="store_true", help="Do not print the report to the terminal (useful when saving to a file).")
    parser.add_argument("--max-file-size", type=int, default=config["max_file_size"], help=f"Maximum file size in bytes (default: {config['max_file_size']})")
    parser.add_argument("--max-total-size", type=int, default=config["max_total_size"], help=f"Maximum total size in bytes (default: {config['max_total_size']})")
    parser.add_argument("--no-cache", action="store_true", help="Disable caching")
    parser.add_argument("--no-static-analysis", action="store_true", help="Disable static analysis")
    parser.add_argument("--config", action="store_true", help="Show current configuration and exit")
    
    args = parser.parse_args()
    
    if args.config:
        print("Current Configuration:")
        print(json.dumps(config, indent=2))
        return
    
    # Check cache first
    cache_key = None
    if not args.no_cache and config["cache_enabled"]:
        cache_key = calculate_project_hash(args.path, args.ignore or [])
        cached_result = get_cached_result(cache_key, config["cache_duration_hours"])
        if cached_result:
            print("\033[92m📄 Using cached analysis result\033[0m")
            if not args.quiet:
                print("\033[1m\033[92m--- Diagnosis Report (Cached) ---\033[0m")
                print(cached_result)
                print("\033[1m\033[92m--- End of Report ---\033[0m")
            
            if args.output:
                try:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        f.write(f"# Enhanced Sophisticated Doctor - Diagnosis Report (Cached)\n\n**Project:** {args.type}\n**Path:** {os.path.abspath(args.path)}\n**Provider:** {args.provider}\n\n---\n\n{cached_result}")
                    print(f"\n\033[92mReport successfully saved to {args.output}\033[0m")
                except Exception as e:
                    print(f"\n\033[91mError: Could not save the report to {args.output}: {e}\033[0m")
            return
    
    api_key = get_api_key(args.provider)
    
    project_content, static_analysis_results, stats = read_project_files(
        args.path, 
        args.ignore, 
        args.verbose,
        args.max_file_size,
        args.max_total_size,
        not args.no_static_analysis
    )
    
    static_analysis_summary = ""
    if not args.no_static_analysis:
        static_analysis_summary = format_static_analysis_summary(static_analysis_results)
    
    show_loading_animation(2.0)
    diagnosis = get_diagnosis(api_key, args.provider, args.type, project_content, static_analysis_summary)
    
    # Cache the result
    if cache_key and not args.no_cache and config["cache_enabled"]:
        save_cached_result(cache_key, diagnosis)
    
    if not args.quiet:
        print("\033[1m\033[92m--- Diagnosis Report ---\033[0m")
        print(diagnosis)
        print("\033[1m\033[92m--- End of Report ---\033[0m")

    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"# Enhanced Sophisticated Doctor - Diagnosis Report\n\n")
                f.write(f"**Project:** {args.type}\n")
                f.write(f"**Path:** {os.path.abspath(args.path)}\n")
                f.write(f"**Provider:** {args.provider}\n")
                f.write(f"**Generated:** {timestamp}\n")
                f.write(f"**Files Processed:** {stats['total_files']}\n")
                f.write(f"**Total Size:** {stats['total_size_kb']:.1f}KB\n\n")
                f.write("---\n\n")
                f.write(diagnosis)
            print(f"\n\033[92mReport successfully saved to {args.output}\033[0m")
        except Exception as e:
            print(f"\n\033[91mError: Could not save the report to {args.output}: {e}\033[0m")

if __name__ == "__main__":
    main()