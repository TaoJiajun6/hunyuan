#!/usr/bin/env python3
"""
简单的前端静态文件服务器
在 8001 端口提供 Web 页面服务
"""
import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

class CORSRequestHandler(SimpleHTTPRequestHandler):
    """支持 CORS 的请求处理器"""
    
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

def run_server(port=8001):
    """启动静态文件服务器"""
    # 获取 web 目录的绝对路径
    web_dir = Path(__file__).parent.absolute()
    os.chdir(web_dir)
    
    server_address = ('', port)
    httpd = HTTPServer(server_address, CORSRequestHandler)
    
    print(f"🚀 前端服务器已启动")
    print(f"📡 访问地址: http://localhost:{port}/")
    print(f"📁 服务目录: {web_dir}")
    print(f"💡 后端 API 地址: http://localhost:8000")
    print(f"⚠️  请确保后端 API 服务器运行在 8000 端口")
    print(f"\n按 Ctrl+C 停止服务器\n")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n服务器已停止")
        httpd.shutdown()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='前端静态文件服务器')
    parser.add_argument('--port', type=int, default=8001, help='服务器端口（默认: 8001）')
    args = parser.parse_args()
    
    run_server(args.port)

