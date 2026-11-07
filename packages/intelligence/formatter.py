from typing import Dict, Any, Optional

class ContentFormatter:

    @classmethod
    def format_telegram_markdown(cls, opp: Dict[str, Any]) -> str:
        """
        Formats opportunity into rich Telegram MarkdownV2 / Markdown syntax.
        """
        role_cat = opp.get("role_category", "full_time").lower()
        company = opp.get("company", "Unknown Company")
        title = opp.get("title", "Job Opening")
        locations = ", ".join(opp.get("locations", [])) or "India / Remote"
        batches = ", ".join(opp.get("eligible_batches", [])) or "Open to all"
        ctc = opp.get("ctc_text") or (f"₹{opp.get('ctc_min')} - {opp.get('ctc_max')} LPA" if opp.get("ctc_min") else "Disclosed in Portal / Best in Industry")
        apply_url = opp.get("apply_url", "")
        deadline = opp.get("deadline") or "Apply ASAP (Rolling Basis)"
        requirements = opp.get("requirements", [])
        
        # 1. Custom Template for Ethara.AI
        if "ethara" in company.lower() or "genops" in title.lower():
            req_bullets = "\n".join([f"• {r}" for r in (requirements or ["Pure English Only (Written & Spoken)", "Prompt evaluation & Instruction following"])])
            return (
                "🎯 *[TARGET ROLE ALERT — ETHARA.AI]*\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🏢 *Company:* {company}\n"
                f"💼 *Role:* {title}\n"
                f"📍 *Location:* {locations}\n"
                f"💰 *Max Package:* {ctc}\n"
                f"🗣️ *Language Requirement:* Pure English Only\n"
                f"⏳ *Status:* Active / Newly Verified\n\n"
                "📋 *Key Requirements:*\n"
                f"{req_bullets}\n\n"
                f"🔗 *Official Application Portal:*\n{apply_url}\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "⚠️ *Action Required:* Review details and submit application directly."
            )

        # 2. Template for Internship
        if "intern" in role_cat or "intern" in title.lower():
            req_bullets = "\n".join([f"• {r}" for r in (requirements[:4] if requirements else ["DSA, OOPs fundamentals", "Proficiency in C++, Java, or Python"])])
            return (
                "🚨 *[OFFICIAL INTERNSHIP ALERT]*\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🏢 *Company:* {company}\n"
                f"🎯 *Role:* {title}\n"
                f"📍 *Location:* {locations}\n"
                f"🎓 *Eligible Batches:* {batches}\n"
                f"💰 *Stipend / CTC:* {ctc}\n"
                f"⏳ *Deadline:* {deadline}\n\n"
                "📌 *Key Requirements:*\n"
                f"{req_bullets}\n\n"
                f"🔗 *Apply Here:* {apply_url}\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "💡 *Tip:* Tailor your resume before applying!"
            )

        # 3. Template for Learning Resource / Roadmap
        if "resource" in role_cat:
            return (
                "📚 *[PLACEMENT PREPARATION RESOURCE]*\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📌 *Topic:* {title}\n"
                f"🛠️ *Source / Creator:* {company}\n"
                f"🎯 *Target Audience:* Batch {batches}\n"
                f"💵 *Cost:* 100% Free\n\n"
                "💡 *Why It's Useful:*\n"
                f"{opp.get('summary') or 'Curated technical interview and placement preparation material.'}\n\n"
                f"🔗 *Direct Access Link:*\n{apply_url}\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )

        # 4. Standard Off-Campus / Full-Time / Mass Hiring
        req_bullets = "\n".join([f"• {r}" for r in (requirements[:4] if requirements else ["Good problem solving & CS fundamentals", "Basic system architecture & coding"])])
        return (
            "🚨 *[OFF-CAMPUS FRESHER HIRING]*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏢 *Company:* {company}\n"
            f"🎯 *Role:* {title}\n"
            f"📍 *Location:* {locations}\n"
            f"🎓 *Eligible Batches:* {batches}\n"
            f"💰 *CTC Package:* {ctc}\n"
            f"⏳ *Status:* Active Recruitment\n\n"
            "📌 *Key Criteria:*\n"
            f"{req_bullets}\n\n"
            f"🔗 *Direct Apply Link:* {apply_url}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📋 *Verified for College Placement Network.*"
        )

    @classmethod
    def format_whatsapp_card(cls, opp: Dict[str, Any]) -> str:
        """
        Formats opportunity into clean WhatsApp text (bold using single asterisks, emoji bullets).
        One-click copy-paste ready for WhatsApp communities.
        """
        company = opp.get("company", "Company")
        title = opp.get("title", "Role Opening")
        locations = ", ".join(opp.get("locations", [])) or "India / Remote"
        batches = ", ".join(opp.get("eligible_batches", [])) or "2026 / 2027"
        ctc = opp.get("ctc_text") or (f"₹{opp.get('ctc_min')} - {opp.get('ctc_max')} LPA" if opp.get("ctc_min") else "Best in Industry")
        apply_url = opp.get("apply_url", "")
        requirements = opp.get("requirements", [])
        
        # Ethara format
        if "ethara" in company.lower() or "genops" in title.lower():
            return (
                f"🎯 *ETHARA.AI HIRING ALERT*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"*Company:* {company}\n"
                f"*Role:* {title}\n"
                f"*Location:* {locations}\n"
                f"*Package:* {ctc}\n"
                f"*Language:* Pure English Only\n\n"
                f"*Apply Link:* {apply_url}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"Apply immediately if matching criteria!"
            )

        # Standard job
        req_str = "\n".join([f"• {r}" for r in requirements[:3]]) if requirements else "• Freshers & eligible graduates"
        return (
            f"🚨 *NEW HIRING OPPORTUNITY*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"*Company:* {company}\n"
            f"*Role:* {title}\n"
            f"*Location:* {locations}\n"
            f"*Eligible Batches:* {batches}\n"
            f"*Package / CTC:* {ctc}\n\n"
            f"*Requirements:*\n{req_str}\n\n"
            f"*Apply here:* {apply_url}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📢 Share with friends & batchmates!"
        )
