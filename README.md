# 简单网站 SEO 检查器

使用 Python 3.10+，无需安装第三方依赖。

默认检查网站：https://aipctool.com。直接运行脚本即可检查，也可以传入其他网址。

```bash
python seo_check.py
python seo_check.py https://aipctool.com
python seo_check.py --json > report.json
# 检查其他网站
python seo_check.py https://example.com
```

检查 HTTP 状态、HTTPS、标题、描述、H1、图片 alt、canonical、HTML 语言、移动端 viewport、noindex 指令，以及站点根目录的 robots.txt 和 sitemap.xml。支持 HTTP 重定向、15 秒超时与单次响应 5 MB 上限。

退出码：0 表示未发现警告；1 表示存在需人工查看的项目；2 表示请求或输入错误。

这是单页面静态 HTML 检查，不执行 JavaScript，也不保证搜索排名或收录。H1 和 canonical 等警告是人工审查提示，并非搜索引擎处罚判定。空 alt 可用于装饰图片，不会被标为缺失。robots.txt 仅检查可访问性和基本内容，不解析爬取权限；sitemap 检查默认路径及 XML 根元素，不查找自定义路径。请仅检查你有权访问的网址。
