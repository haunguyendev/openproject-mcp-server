# Hướng dẫn Publish lên npm

Tài liệu này hướng dẫn cách publish OpenProject MCP Server lên npm để users có thể dùng với `npx`.

## Prerequisites

1. **npm account**: Đăng ký tại https://www.npmjs.com/signup
2. **npm CLI**: Đã cài đặt Node.js (bao gồm npm)
3. **Organization** (optional): Tạo organization trên npm nếu publish dưới org scope

## Bước 1: Setup npm Package

### 1.1. Update package.json

Sửa file [package.json](package.json):

```json
{
  "name": "@your-org/server-openproject",  // Thay your-org bằng org name thật
  "version": "1.0.0",
  "author": "Your Name <email@example.com>",  // Thay thông tin của bạn
  "repository": {
    "url": "https://github.com/your-org/openproject-mcp-server"  // Thay repo URL
  }
}
```

**Lưu ý về package name:**
- Scoped package (có `@`): `@your-org/server-openproject`
- Unscoped package: `server-openproject-mcp` (cần check available trên npm)

### 1.2. Test local

```bash
# Test bin script hoạt động
chmod +x bin/run.js  # macOS/Linux only
node bin/run.js

# Test với npx local
npm link
npx @your-org/server-openproject
```

## Bước 2: Login vào npm

```bash
npm login
```

Nhập:
- Username
- Password
- Email
- OTP (nếu có 2FA)

Verify:
```bash
npm whoami
```

## Bước 3: Publish

### 3.1. Publish lần đầu

**Public package** (free):
```bash
npm publish --access public
```

**Private package** (cần npm Pro/Teams):
```bash
npm publish
```

### 3.2. Publish updates

Mỗi lần update:

```bash
# 1. Update version trong package.json
npm version patch  # 1.0.0 → 1.0.1
# hoặc
npm version minor  # 1.0.0 → 1.1.0
# hoặc
npm version major  # 1.0.0 → 2.0.0

# 2. Publish
npm publish --access public

# 3. Commit version bump
git add package.json
git commit -m "Bump version to $(node -p \"require('./package.json').version\")"
git push
```

## Bước 4: User Configuration

Sau khi publish, users sẽ config như sau:

### Claude Desktop config

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "openproject": {
      "command": "npx",
      "args": [
        "-y",
        "@your-org/server-openproject"
      ],
      "env": {
        "OPENPROJECT_API_URL": "https://your-instance.openproject.com",
        "OPENPROJECT_API_KEY": "your-api-key-here",
        "OPENPROJECT_PROXY": "http://proxy:3128",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

**Lưu ý**:
- `npx -y`: Auto-confirm install
- Package name phải khớp với name trong `package.json`
- Environment variables được pass qua `env` object

## Bước 5: Maintenance

### 5.1. Update package

```bash
# 1. Make code changes
# 2. Test local
npm link
npx @your-org/server-openproject

# 3. Update version và publish
npm version patch
npm publish --access public

# 4. Commit
git add package.json
git commit -m "Release v$(node -p \"require('./package.json').version\")"
git tag v$(node -p "require('./package.json').version")
git push --tags
git push
```

### 5.2. Deprecate version

```bash
npm deprecate @your-org/server-openproject@1.0.0 "This version has bugs, use 1.0.1+"
```

### 5.3. Unpublish (chỉ trong 72h đầu)

```bash
npm unpublish @your-org/server-openproject@1.0.0
```

## Verification

### Check package được publish

```bash
npm view @your-org/server-openproject
```

### Test installation

```bash
npx @your-org/server-openproject@latest
```

## Alternative: Unscoped Package

Nếu không muốn dùng organization scope:

### package.json
```json
{
  "name": "mcp-server-openproject",
  "bin": {
    "mcp-server-openproject": "./bin/run.js"
  }
}
```

### Claude config
```json
{
  "mcpServers": {
    "openproject": {
      "command": "npx",
      "args": ["-y", "mcp-server-openproject"]
    }
  }
}
```

**Lưu ý**:
- Unscoped names phải unique globally trên npm
- Check available: `npm search mcp-server-openproject`

## Best Practices

### 1. Versioning
- Follow semantic versioning (semver): MAJOR.MINOR.PATCH
- Breaking changes → MAJOR bump
- New features → MINOR bump
- Bug fixes → PATCH bump

### 2. Documentation
- Update README.md với npm install instructions
- Add CHANGELOG.md để track changes
- Include examples trong README

### 3. Testing
- Test local trước khi publish: `npm link`
- Test trên clean machine sau khi publish
- Setup CI/CD để auto-publish từ GitHub releases

### 4. Security
- Enable 2FA trên npm account
- Use `.npmignore` để exclude sensitive files:
  ```
  .env
  .venv/
  __pycache__/
  *.pyc
  tests/
  .git/
  ```

## CI/CD Auto-Publish (Optional)

Setup GitHub Actions để auto-publish khi tag:

### .github/workflows/npm-publish.yml
```yaml
name: Publish to npm

on:
  push:
    tags:
      - 'v*'

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
          registry-url: 'https://registry.npmjs.org'
      - run: npm publish --access public
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```

**Setup**:
1. Tạo npm access token: https://www.npmjs.com/settings/tokens
2. Add vào GitHub Secrets: Settings > Secrets > NPM_TOKEN

## Troubleshooting

### Error: "Package name already exists"
- Đổi name trong package.json
- Hoặc dùng scoped name: `@your-org/server-openproject`

### Error: "You must be logged in"
```bash
npm login
npm whoami
```

### Error: "Python not found" (user-side)
Users cần install Python 3.10+:
- Windows: https://www.python.org/downloads/
- macOS: `brew install python3`
- Linux: `sudo apt install python3`

### Error: "Permission denied" khi chạy bin script
```bash
chmod +x bin/run.js
```

## Support

- npm docs: https://docs.npmjs.com/
- Semantic versioning: https://semver.org/
- npm package naming: https://docs.npmjs.com/cli/v10/configuring-npm/package-json#name

---

**Version**: 1.0
**Last Updated**: 2025-01-XX
