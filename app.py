"""
红利低波跟踪系统 — 启动入口

极简启动：
  python app.py
"""

import os
from flask import Flask
from server.routes import bp, init_db


def create_app():
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder='server/templates',
    )
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

    app.register_blueprint(bp)

    # 初始化数据库
    with app.app_context():
        init_db()

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5050)
