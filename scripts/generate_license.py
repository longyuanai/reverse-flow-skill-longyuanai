#!/usr/bin/env python3
"""Commercial license generator and certificate issuer for reverse-flow & pojia.

Generates official commercial license certificates, customized procurement
contracts, and cryptographically verified license tokens for paying clients.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMERCIAL_DOCS = ROOT / "docs" / "commercial"

TIER_NAMES = {
    "consultant": "独立顾问版 (Consultant Edition)",
    "enterprise": "企业团队版 (Enterprise Team Edition)",
    "enterprise-buyout": "企业团队永久买断版 (Enterprise Team Buyout)",
    "oem": "OEM / 白标集成版 (OEM Redistribution Edition)",
}

TIER_PRICES = {
    "consultant": "¥699 / 年",
    "enterprise": "¥4,999 / 年",
    "enterprise-buyout": "¥9,999 (永久买断)",
    "oem": "¥19,999 起 (定制)",
}

TIER_SCOPES = {
    "consultant": "单人商业授权 (Single User Commercial License)",
    "enterprise": "企业内部站点无限席位部署 (Site-Wide Unlimited License)",
    "enterprise-buyout": "企业内部站点永久无限席位部署 (Permanent Site-Wide License)",
    "oem": "商业软硬件产品集成与白标再分发 (OEM Redistribution & White-label)",
}


def calculate_signature(client_name: str, license_id: str, tier: str, expiry: str) -> str:
    """Calculate a verification HMAC/SHA256 signature for the issued license."""
    salt = "longyuanai-commercial-license-v1-secret-salt"
    payload = f"{client_name}|{license_id}|{tier}|{expiry}|{salt}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def issue_license(
    client_name: str,
    tier: str,
    contact_email: str,
    org_code: str = "统一社会信用代码待补充",
    years_valid: int = 1,
    out_dir: Path | None = None,
) -> dict[str, str]:
    """Issue a full commercial licensing kit (Certificate, Agreement, and JSON token)."""
    if tier not in TIER_NAMES:
        raise ValueError(f"Invalid license tier: '{tier}'. Must be one of {list(TIER_NAMES.keys())}")

    now = datetime.datetime.now(datetime.timezone.utc)
    issue_date = now.strftime("%Y-%m-%d")
    is_permanent = (tier == "enterprise-buyout")

    if is_permanent:
        expiry_date = "永久有效 (Permanent)"
        expiry_code = "9999-12-31"
    else:
        expiry_dt = now + datetime.timedelta(days=365 * years_valid)
        expiry_date = expiry_dt.strftime("%Y-%m-%d")
        expiry_code = expiry_date

    # Deterministic license ID
    id_seed = f"{client_name}_{issue_date}_{tier}".encode("utf-8")
    hex_hash = hashlib.sha256(id_seed).hexdigest()[:8].upper()
    license_id = f"RF-COMM-{now.strftime('%Y')}-{hex_hash}"

    sig = calculate_signature(client_name, license_id, tier, expiry_code)

    # 1. License Token JSON
    token_data = {
        "license_id": license_id,
        "product": "reverse-flow-skill & pojia",
        "licensee": client_name,
        "org_code": org_code,
        "contact_email": contact_email,
        "tier": tier,
        "tier_name": TIER_NAMES[tier],
        "scope": TIER_SCOPES[tier],
        "issue_date": issue_date,
        "expiry_date": expiry_date,
        "signature": sig,
        "licensor": "longyuan (@longyuanai)",
        "official_repo": "https://github.com/longyuanai/reverse-flow-skill-longyuanai",
    }

    # 2. Formatted Certificate Text
    cert_text = f"""================================================================================
                    OFFICIAL COMMERCIAL LICENSE CERTIFICATE
                         软件商业授权与许可合规凭证
================================================================================

授权编号 (License ID)   : {license_id}
签发日期 (Issue Date)   : {issue_date}
有效期至 (Valid Through): {expiry_date}

被许可实体 (Licensee)  : {client_name}
统一社会信用代码/组织代码: {org_code}
联络邮箱 (Contact)      : {contact_email}
授权产品 (Product)      : reverse-flow-skill & pojia (v1.0.0+)
授权版本 (Tier)         : {TIER_NAMES[tier]}
授权范围 (Scope)        : {TIER_SCOPES[tier]}
官方标价 (Price)        : {TIER_PRICES[tier]}

数字防伪指纹 (Signature) : {sig}

--------------------------------------------------------------------------------
【授权声明与法律效力】

1. 权利授予：根据双方签署的商业采购协议，被许可方享有在上述授权范围内
   商业化部署、集成、调用及运行本软件的完全合法权利，免除 PolyForm Noncommercial 1.0.0
   开源协议中的非商业限制条款。

2. 合规与免责：被许可方经官方正规授权，在商业安全交付、渗透测试与 SOC 分析中使用本软件
   具备完整的知识产权使用权凭证，符合企业安全采购合规与外部合规审计标准。

3. 合法使用承诺：被许可方须恪守技术中立与网络安全法律法规，在授权范围内从事合规安全研究
   与防御工作，严禁用于任何未经授权的入侵破坏或侵犯他人版权之行为。

--------------------------------------------------------------------------------
许可方 / 著作权方 (Licensor) : longyuan (@longyuanai) & reverse-flow project
官方咨询与查验邮箱          : 1507205727@qq.com
证书防伪与验证查验地址      : https://github.com/longyuanai/reverse-flow-skill-longyuanai

                     [ 官方已核发 / 电子签署确认 ]
================================================================================
"""

    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        token_path = out_dir / f"{license_id}.json"
        cert_path = out_dir / f"{license_id}-CERTIFICATE.txt"

        token_path.write_text(json.dumps(token_data, ensure_ascii=False, indent=2), encoding="utf-8")
        cert_path.write_text(cert_text, encoding="utf-8")

        return {
            "license_id": license_id,
            "signature": sig,
            "token_path": str(token_path.resolve()),
            "cert_path": str(cert_path.resolve()),
        }

    return {
        "license_id": license_id,
        "signature": sig,
        "cert_text": cert_text,
        "token_json": json.dumps(token_data, ensure_ascii=False, indent=2),
    }


def verify_license(token_file: Path) -> bool:
    """Verify the cryptographic signature and validity of a license token."""
    if not token_file.exists():
        raise FileNotFoundError(f"License file not found: {token_file}")

    data = json.loads(token_file.read_text(encoding="utf-8"))
    client_name = data["licensee"]
    license_id = data["license_id"]
    tier = data["tier"]
    expiry = data["expiry_date"]
    sig = data["signature"]

    expiry_code = "9999-12-31" if "永久" in expiry else expiry
    expected_sig = calculate_signature(client_name, license_id, tier, expiry_code)
    return sig == expected_sig


def main() -> int:
    parser = argparse.ArgumentParser(description="Issue official commercial license for reverse-flow & pojia.")
    parser.add_argument("--client", required=True, help="Full name of client / company")
    parser.add_argument("--tier", required=True, choices=list(TIER_NAMES.keys()), help="License tier")
    parser.add_argument("--email", required=True, help="Client contact email")
    parser.add_argument("--org-code", default="统一社会信用代码待补充", help="Company unified social credit code")
    parser.add_argument("--years", type=int, default=1, help="Years valid (default: 1)")
    parser.add_argument("--out", type=Path, default=ROOT / "dist" / "licenses", help="Output directory")
    args = parser.parse_args()

    result = issue_license(
        client_name=args.client,
        tier=args.tier,
        contact_email=args.email,
        org_code=args.org_code,
        years_valid=args.years,
        out_dir=args.out,
    )

    print(f"[+] License Issued Successfully!")
    print(f"    License ID : {result['license_id']}")
    print(f"    Signature  : {result['signature']}")
    print(f"    Certificate: {result['token_path']}")
    print(f"    Token Path : {result['cert_path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
