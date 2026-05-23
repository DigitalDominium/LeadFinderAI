from __future__ import annotations

"""
AI Lead Finder — Full Rebuild
Contract Logistics Sales CRM
By David Raja  |  Digital Dominium Enterprise  |  2026
"""

import threading
import traceback
import urllib.parse
import webbrowser
from datetime import datetime, date
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any

import customtkinter as ctk

import database as db
from config import (
    OPENAI_MODEL, PIPELINE_STAGES, STAGE_COLORS, PRIORITY_COLORS
)
from services.google_maps import find_business_leads, GoogleMapsError
from services.ai_analyzer import analyze_lead_with_ai
from services.exporter import export_leads_to_excel


# ── Theme ─────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Palette
BG_BASE      = "#0D0F1A"
BG_SURFACE   = "#141627"
BG_CARD      = "#1C2035"
BG_ELEVATED  = "#232640"
ACCENT       = "#4F7EFF"
ACCENT_HOVER = "#3D6AE8"
ACCENT_GREEN = "#10B981"
ACCENT_RED   = "#EF4444"
ACCENT_AMBER = "#F59E0B"
TEXT_PRIMARY  = "#F0F2FF"
TEXT_SECONDARY= "#8892B0"
TEXT_DIM      = "#4A5568"
BORDER        = "#2A2F4A"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _label(parent, text, size=13, weight="normal", color=TEXT_PRIMARY, **kw):
    return ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(size=size, weight=weight),
                        text_color=color, **kw)


def _btn(parent, text, command, fg=ACCENT, hover=ACCENT_HOVER, width=140, **kw):
    return ctk.CTkButton(parent, text=text, command=command,
                         fg_color=fg, hover_color=hover, width=width,
                         font=ctk.CTkFont(size=12, weight="bold"),
                         corner_radius=8, **kw)


def _entry(parent, placeholder="", width=None, **kw):
    kwargs = dict(placeholder_text=placeholder,
                  fg_color=BG_ELEVATED, border_color=BORDER,
                  text_color=TEXT_PRIMARY, corner_radius=6)
    if width:
        kwargs["width"] = width
    kwargs.update(kw)
    return ctk.CTkEntry(parent, **kwargs)


def _separator(parent, **kw):
    return ctk.CTkFrame(parent, height=1, fg_color=BORDER, **kw)


# ── Main Window ───────────────────────────────────────────────────────────────

class AILeadFinderApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.configure(fg_color=BG_BASE)
        self.title("AI Lead Finder  ·  Contract Logistics CRM  ·  Digital Dominium Enterprise")
        self.geometry("1400x860")
        self.minsize(1200, 720)

        db.init_db()

        self._prospect_leads: list[dict] = []
        self._prospect_filtered: list[dict] = []
        self._selected_prospect: dict | None = None

        self._pipeline_leads: list[dict] = []
        self._selected_pipeline: dict | None = None

        self._build_header()
        self._build_tabs()
        self._refresh_pipeline()
        self._refresh_followups()
        self._refresh_analytics()

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=BG_SURFACE, corner_radius=0, height=58)
        hdr.pack(fill="x", side="top")
        hdr.pack_propagate(False)

        ctk.CTkLabel(
            hdr, text="  🚀  AI Lead Finder",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(side="left", padx=20, pady=0)

        ctk.CTkLabel(
            hdr, text="Contract Logistics Sales CRM  ·  Digital Dominium Enterprise",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_SECONDARY,
        ).pack(side="left", padx=4)

        self._clock_label = ctk.CTkLabel(hdr, text="", text_color=TEXT_DIM,
                                          font=ctk.CTkFont(size=11))
        self._clock_label.pack(side="right", padx=20)
        self._tick_clock()

    def _tick_clock(self):
        self._clock_label.configure(
            text=datetime.now().strftime("%a, %d %b %Y  %H:%M:%S")
        )
        self.after(1000, self._tick_clock)

    # ── Tab Container ─────────────────────────────────────────────────────────

    def _build_tabs(self):
        self.tabview = ctk.CTkTabview(
            self,
            fg_color=BG_BASE,
            segmented_button_fg_color=BG_SURFACE,
            segmented_button_selected_color=ACCENT,
            segmented_button_selected_hover_color=ACCENT_HOVER,
            segmented_button_unselected_color=BG_SURFACE,
            segmented_button_unselected_hover_color=BG_ELEVATED,
            text_color=TEXT_PRIMARY,
            text_color_disabled=TEXT_DIM,
            border_width=0,
            corner_radius=0,
        )
        self.tabview.pack(fill="both", expand=True, padx=0, pady=0)

        for tab_name in ["🔍  Prospect", "📋  Pipeline", "📅  Follow-ups", "📊  Analytics"]:
            self.tabview.add(tab_name)

        self._build_prospect_tab(self.tabview.tab("🔍  Prospect"))
        self._build_pipeline_tab(self.tabview.tab("📋  Pipeline"))
        self._build_followup_tab(self.tabview.tab("📅  Follow-ups"))
        self._build_analytics_tab(self.tabview.tab("📊  Analytics"))

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — PROSPECT
    # ══════════════════════════════════════════════════════════════════════════

    def _build_prospect_tab(self, parent):
        parent.configure(fg_color=BG_BASE)
        parent.grid_columnconfigure(1, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        # ── Sidebar ──
        sidebar = ctk.CTkFrame(parent, fg_color=BG_SURFACE, corner_radius=12, width=300)
        sidebar.grid(row=0, column=0, sticky="nsew", padx=(12,6), pady=12)
        sidebar.grid_propagate(False)
        sidebar.grid_columnconfigure(0, weight=1)

        _label(sidebar, "Search Parameters", 15, "bold").grid(
            row=0, column=0, padx=16, pady=(20,4), sticky="w")
        _separator(sidebar).grid(row=1, column=0, sticky="ew", padx=12, pady=(0,12))

        params = [
            ("Location / Area",            "Tuas, Singapore",                    "p_location"),
            ("Industry / Keyword",          "manufacturing",                      "p_industry"),
            ("Radius (km)",                 "10",                                 "p_radius"),
            ("Lead Count",                  "10",                                 "p_count"),
            ("Target Service",              "Warehousing, VAS, inventory mgmt",  "p_service"),
            ("OpenAI Model",                OPENAI_MODEL,                         "p_model"),
        ]
        for i, (lbl, default, attr) in enumerate(params):
            row = 2 + i * 2
            _label(sidebar, lbl, 11, color=TEXT_SECONDARY).grid(
                row=row, column=0, padx=16, pady=(0,2), sticky="w")
            e = _entry(sidebar, default)
            e.insert(0, default)
            e.grid(row=row+1, column=0, padx=12, pady=(0,8), sticky="ew")
            setattr(self, attr, e)

        _separator(sidebar).grid(row=14, column=0, sticky="ew", padx=12, pady=8)

        self._p_find_btn = _btn(sidebar, "🔍  Find Leads", self._prospect_find, width=260)
        self._p_find_btn.grid(row=15, column=0, padx=16, pady=(4,6), sticky="ew")

        self._p_analyze_btn = _btn(sidebar, "🤖  Analyze All with AI", self._prospect_analyze,
                                   fg=BG_ELEVATED, hover="#2E3355", width=260)
        self._p_analyze_btn.grid(row=16, column=0, padx=16, pady=6, sticky="ew")

        self._p_save_btn = _btn(sidebar, "💾  Save All to Pipeline", self._prospect_save_all,
                                fg=ACCENT_GREEN, hover="#0EA271", width=260)
        self._p_save_btn.grid(row=17, column=0, padx=16, pady=6, sticky="ew")

        self._p_export_btn = _btn(sidebar, "📤  Export to Excel", self._prospect_export,
                                  fg=BG_ELEVATED, hover="#2E3355", width=260)
        self._p_export_btn.grid(row=18, column=0, padx=16, pady=6, sticky="ew")

        _btn(sidebar, "🗑  Clear Session", self._prospect_clear,
             fg="#2A1A1A", hover="#3D1F1F", width=260).grid(
            row=19, column=0, padx=16, pady=6, sticky="ew")

        self._p_progress = ctk.CTkProgressBar(sidebar, progress_color=ACCENT,
                                               fg_color=BG_ELEVATED)
        self._p_progress.grid(row=20, column=0, padx=16, pady=(16,4), sticky="ew")
        self._p_progress.set(0)

        self._p_status = _label(sidebar, "Ready", 11, color=TEXT_SECONDARY, wraplength=260, justify="left")
        self._p_status.grid(row=21, column=0, padx=16, pady=(2,20), sticky="w")

        # ── Main content ──
        content = ctk.CTkFrame(parent, fg_color=BG_BASE)
        content.grid(row=0, column=1, sticky="nsew", padx=(6,12), pady=12)
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(1, weight=3)
        content.grid_rowconfigure(3, weight=2)

        # Filter bar
        filter_bar = ctk.CTkFrame(content, fg_color=BG_SURFACE, corner_radius=10)
        filter_bar.grid(row=0, column=0, sticky="ew", pady=(0,8))
        filter_bar.grid_columnconfigure(1, weight=1)

        _label(filter_bar, "Filter:", 12).grid(row=0, column=0, padx=12, pady=10)
        self._p_filter = _entry(filter_bar,
                                 "Filter by company, address, priority, service…")
        self._p_filter.grid(row=0, column=1, sticky="ew", padx=(0,8), pady=8)
        self._p_filter.bind("<KeyRelease>", lambda _: self._prospect_apply_filter())

        self._p_count_label = _label(filter_bar, "0 leads", 11, color=TEXT_SECONDARY)
        self._p_count_label.grid(row=0, column=2, padx=12)

        # Table
        self._p_table_frame = ctk.CTkFrame(content, fg_color=BG_SURFACE, corner_radius=10)
        self._p_table_frame.grid(row=1, column=0, sticky="nsew", pady=(0,8))
        self._build_prospect_table(self._p_table_frame)

        # Detail bar
        detail_bar = ctk.CTkFrame(content, fg_color="transparent")
        detail_bar.grid(row=2, column=0, sticky="ew", pady=(4,4))
        detail_bar.grid_columnconfigure(0, weight=1)

        _label(detail_bar, "Lead Details  /  AI Sales Brief", 14, "bold").grid(
            row=0, column=0, sticky="w")

        btn_frame = ctk.CTkFrame(detail_bar, fg_color="transparent")
        btn_frame.grid(row=0, column=1)

        self._p_linkedin_btn = _btn(btn_frame, "👤  Find Contacts", self._open_linkedin_people,
                                    fg="#0A66C2", hover="#004182", width=160)
        self._p_linkedin_btn.pack(side="left", padx=4)
        self._p_linkedin_btn.configure(state="disabled")

        self._p_web_btn = _btn(btn_frame, "🌐  Visit Website", self._open_website,
                               fg="#0A66C2", hover="#004182", width=150)
        self._p_web_btn.pack(side="left", padx=4)
        self._p_web_btn.configure(state="disabled")

        self._p_save_one_btn = _btn(btn_frame, "➕  Save to Pipeline", self._prospect_save_one,
                                    fg=ACCENT_GREEN, hover="#0EA271", width=165)
        self._p_save_one_btn.pack(side="left", padx=4)
        self._p_save_one_btn.configure(state="disabled")

        self._p_copy_email_btn = _btn(btn_frame, "📋  Copy Email", self._copy_email_draft,
                                      fg=ACCENT_AMBER, hover="#D97706", width=140)
        self._p_copy_email_btn.pack(side="left", padx=4)
        self._p_copy_email_btn.configure(state="disabled")

        self._p_copy_wa_btn = _btn(btn_frame, "💬  Copy WhatsApp", self._copy_whatsapp,
                                   fg="#25D366", hover="#1DB954", width=160)
        self._p_copy_wa_btn.pack(side="left", padx=4)
        self._p_copy_wa_btn.configure(state="disabled")

        # Detail textbox
        self._p_detail = ctk.CTkTextbox(content, height=180, wrap="word",
                                         fg_color=BG_SURFACE, text_color=TEXT_PRIMARY,
                                         corner_radius=10, font=ctk.CTkFont(size=12))
        self._p_detail.grid(row=3, column=0, sticky="nsew")
        self._p_detail.insert("1.0", "Select a lead to view AI sales brief here.")
        self._p_detail.configure(state="disabled")

    def _build_prospect_table(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        import tkinter.ttk as ttk

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Prospect.Treeview",
                         background=BG_CARD, foreground=TEXT_PRIMARY,
                         fieldbackground=BG_CARD, rowheight=28,
                         borderwidth=0, font=("Segoe UI", 11))
        style.configure("Prospect.Treeview.Heading",
                         background=BG_ELEVATED, foreground=TEXT_SECONDARY,
                         relief="flat", font=("Segoe UI", 11, "bold"))
        style.map("Prospect.Treeview",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", "#FFFFFF")])

        cols = ("name","address","phone","score","priority","service","stage")
        self._p_tree = ttk.Treeview(parent, columns=cols, show="headings",
                                     style="Prospect.Treeview")

        hdrs = [("name","Company",220),("address","Address",310),("phone","Phone",110),
                ("score","Score",65),("priority","Priority",85),
                ("service","Suggested Service",220),("stage","Stage",90)]
        for col, text, w in hdrs:
            self._p_tree.heading(col, text=text,
                                  command=lambda c=col: self._prospect_sort(c))
            self._p_tree.column(col, width=w,
                                 anchor="center" if col in ("score","priority","stage") else "w")

        self._p_tree.tag_configure("HIGH",   background="#2A1515")
        self._p_tree.tag_configure("MEDIUM", background="#2A2010")
        self._p_tree.tag_configure("LOW",    background=BG_CARD)

        self._p_tree.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self._p_tree.bind("<<TreeviewSelect>>", self._prospect_on_select)

        sb = ttk.Scrollbar(parent, orient="vertical", command=self._p_tree.yview)
        sb.grid(row=0, column=1, sticky="ns", pady=8)
        self._p_tree.configure(yscrollcommand=sb.set)

    # ── Prospect actions ──────────────────────────────────────────────────────

    def _prospect_set_status(self, text, progress=None):
        self._p_status.configure(text=text)
        if progress is not None:
            self._p_progress.set(max(0, min(float(progress), 1)))
        self.update_idletasks()

    def _prospect_buttons(self, state):
        for b in [self._p_find_btn, self._p_analyze_btn,
                  self._p_save_btn, self._p_export_btn]:
            b.configure(state=state)

    def _prospect_find(self):
        def worker():
            try:
                self._prospect_buttons("disabled")
                self._prospect_set_status("Searching Google Places…", 0.1)
                loc = self.p_location.get().strip()
                ind = self.p_industry.get().strip()
                rad = float(self.p_radius.get().strip() or 10)
                cnt = int(float(self.p_count.get().strip() or 10))
                if not loc or not ind:
                    raise ValueError("Please enter both Location and Industry keyword.")
                leads, fmt_loc = find_business_leads(loc, ind, rad, cnt)
                self._prospect_leads = leads
                self._prospect_filtered = leads[:]
                self._prospect_refresh_table()
                self._prospect_set_status(f"Found {len(leads)} leads near {fmt_loc}.", 1.0)
            except (GoogleMapsError, ValueError) as e:
                self._prospect_set_status("Search failed.", 0)
                messagebox.showerror("Search Failed", str(e))
            except Exception as e:
                self._prospect_set_status("Unexpected error.", 0)
                messagebox.showerror("Error", f"{e}\n\n{traceback.format_exc()}")
            finally:
                self._prospect_buttons("normal")
        threading.Thread(target=worker, daemon=True).start()

    def _prospect_analyze(self):
        def worker():
            try:
                if not self._prospect_leads:
                    messagebox.showinfo("No Leads", "Find leads first.")
                    return
                self._prospect_buttons("disabled")
                svc = self.p_service.get().strip()
                mdl = self.p_model.get().strip()
                total = len(self._prospect_leads)
                for i, lead in enumerate(self._prospect_leads, 1):
                    self._prospect_set_status(
                        f"AI analysing {i}/{total}: {lead.get('name','')}", i/max(total,1))
                    result = analyze_lead_with_ai(lead, svc, model=mdl)
                    lead.update(result)
                    self._prospect_refresh_table()
                self._prospect_apply_filter()
                self._prospect_set_status(f"Analysis complete for {total} leads.", 1.0)
            except Exception as e:
                self._prospect_set_status("AI analysis failed.", 0)
                messagebox.showerror("AI Error", f"{e}\n\n{traceback.format_exc()}")
            finally:
                self._prospect_buttons("normal")
        threading.Thread(target=worker, daemon=True).start()

    def _prospect_save_all(self):
        if not self._prospect_leads:
            messagebox.showinfo("No Leads", "Find leads first.")
            return
        saved = 0
        for lead in self._prospect_leads:
            if lead.get("place_id"):
                db.upsert_lead(lead)
                saved += 1
        messagebox.showinfo("Saved", f"{saved} leads saved to Pipeline.")
        self._refresh_pipeline()
        self._refresh_analytics()

    def _prospect_save_one(self):
        lead = self._selected_prospect
        if not lead:
            return
        if not lead.get("place_id"):
            messagebox.showwarning("Cannot Save", "No place ID for this lead.")
            return
        db.upsert_lead(lead)
        self._refresh_pipeline()
        self._refresh_analytics()
        messagebox.showinfo("Saved", f"'{lead.get('name','')}' added to Pipeline.")

    def _prospect_export(self):
        if not self._prospect_leads:
            messagebox.showinfo("No Leads", "No leads to export.")
            return
        path = filedialog.asksaveasfilename(
            title="Save Excel", defaultextension=".xlsx",
            filetypes=[("Excel","*.xlsx")], initialfile="AI_Leads_Export.xlsx")
        if not path:
            return
        try:
            export_leads_to_excel(self._prospect_leads, Path(path))
            messagebox.showinfo("Exported", f"Saved to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    def _prospect_clear(self):
        self._prospect_leads = []
        self._prospect_filtered = []
        self._selected_prospect = None
        self._prospect_refresh_table()
        self._prospect_set_detail("Session cleared. Ready for new search.")
        self._prospect_set_status("Ready", 0)
        for b in [self._p_linkedin_btn, self._p_web_btn,
                  self._p_save_one_btn, self._p_copy_email_btn, self._p_copy_wa_btn]:
            b.configure(state="disabled")

    def _prospect_apply_filter(self):
        q = self._p_filter.get().strip().lower()
        if not q:
            self._prospect_filtered = self._prospect_leads[:]
        else:
            self._prospect_filtered = [
                l for l in self._prospect_leads
                if q in " ".join(str(v).lower() for v in l.values())
            ]
        self._prospect_refresh_table()

    def _prospect_refresh_table(self):
        for item in self._p_tree.get_children():
            self._p_tree.delete(item)
        for idx, lead in enumerate(self._prospect_filtered):
            pri = lead.get("priority", "") or ""
            self._p_tree.insert("", "end", iid=str(idx), tags=(pri,), values=(
                lead.get("name",""),
                lead.get("address",""),
                lead.get("phone",""),
                lead.get("lead_score",""),
                pri,
                lead.get("suggested_service",""),
                lead.get("stage","New"),
            ))
        self._p_count_label.configure(text=f"{len(self._prospect_filtered)} leads")

    def _prospect_sort(self, col):
        reverse = getattr(self, f"_sort_{col}_rev", False)
        self._prospect_filtered.sort(
            key=lambda x: (x.get(col) or ""), reverse=reverse)
        setattr(self, f"_sort_{col}_rev", not reverse)
        self._prospect_refresh_table()

    def _prospect_on_select(self, _=None):
        sel = self._p_tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        if idx >= len(self._prospect_filtered):
            return
        self._selected_prospect = self._prospect_filtered[idx]
        self._prospect_set_detail(self._format_lead_detail(self._selected_prospect))
        for b in [self._p_linkedin_btn, self._p_web_btn,
                  self._p_save_one_btn, self._p_copy_email_btn, self._p_copy_wa_btn]:
            b.configure(state="normal")

    def _prospect_set_detail(self, text):
        self._p_detail.configure(state="normal")
        self._p_detail.delete("1.0", "end")
        self._p_detail.insert("1.0", text)
        self._p_detail.configure(state="disabled")

    def _open_linkedin_people(self):
        lead = self._selected_prospect
        if not lead:
            return
        company = lead.get("name","").strip()
        role_var = getattr(self, "_linkedin_role", None)
        role = role_var.get() if role_var else "Supply Chain Manager"
        q = urllib.parse.quote(f"{company} {role}")
        webbrowser.open(f"https://www.linkedin.com/search/results/people/?keywords={q}&origin=FACETED_SEARCH")

    def _open_website(self):
        lead = self._selected_prospect
        if not lead:
            return
        url = lead.get("website","").strip()
        if url:
            webbrowser.open(url)
        else:
            name = urllib.parse.quote(lead.get("name",""))
            webbrowser.open(f"https://www.google.com/search?q={name}")

    def _copy_email_draft(self):
        lead = self._selected_prospect
        if not lead:
            return
        subj = lead.get("email_subject","")
        body = lead.get("email_body","")
        if not subj and not body:
            messagebox.showinfo("No Draft", "Run AI analysis first to generate email draft.")
            return
        self.clipboard_clear()
        self.clipboard_append(f"Subject: {subj}\n\n{body}")
        messagebox.showinfo("Copied", "Email draft copied to clipboard!")

    def _copy_whatsapp(self):
        lead = self._selected_prospect
        if not lead:
            return
        msg = lead.get("whatsapp_draft","")
        if not msg:
            messagebox.showinfo("No Draft", "Run AI analysis first to generate WhatsApp draft.")
            return
        self.clipboard_clear()
        self.clipboard_append(msg)
        messagebox.showinfo("Copied", "WhatsApp message copied to clipboard!")

    def _format_lead_detail(self, lead: dict) -> str:
        lines = [
            "━━  COMPANY  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"Name:     {lead.get('name','')}",
            f"Address:  {lead.get('address','')}",
            f"Phone:    {lead.get('phone','')}",
            f"Website:  {lead.get('website','')}",
            f"Maps:     {lead.get('google_maps_url','')}",
            f"Status:   {lead.get('business_status','')}  |  Rating: {lead.get('rating','')} ({lead.get('user_rating_count','')} reviews)",
            f"Type:     {lead.get('primary_type','')}",
            "",
            "━━  AI SALES ANALYSIS  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"Score:          {lead.get('lead_score','')} / 100   |   Priority: {lead.get('priority','')}",
            f"Potential:      {lead.get('logistics_potential','')}",
            f"Suggested Svc:  {lead.get('suggested_service','')}",
            f"Pain Points:    {lead.get('possible_pain_points','')}",
            f"Reasoning:      {lead.get('reasoning_summary','')}",
            "",
            "━━  OPENING LINE  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            lead.get('sales_opening_line',''),
            "",
            "━━  WHATSAPP DRAFT  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            lead.get('whatsapp_draft',''),
            "",
            "━━  EMAIL DRAFT  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"Subject: {lead.get('email_subject','')}",
            "",
            lead.get('email_body',''),
        ]
        return "\n".join(lines)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — PIPELINE
    # ══════════════════════════════════════════════════════════════════════════

    def _build_pipeline_tab(self, parent):
        parent.configure(fg_color=BG_BASE)
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        # ── Top bar ──
        top = ctk.CTkFrame(parent, fg_color=BG_SURFACE, corner_radius=10)
        top.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        top.grid_columnconfigure(3, weight=1)

        _label(top, "Stage:", 12).grid(row=0, column=0, padx=12, pady=10)
        self._pl_stage_var = ctk.StringVar(value="All")
        stage_opts = ["All"] + PIPELINE_STAGES
        self._pl_stage_menu = ctk.CTkOptionMenu(
            top, values=stage_opts, variable=self._pl_stage_var,
            command=lambda _: self._refresh_pipeline(),
            fg_color=BG_ELEVATED, button_color=ACCENT,
            button_hover_color=ACCENT_HOVER, text_color=TEXT_PRIMARY, width=130)
        self._pl_stage_menu.grid(row=0, column=1, padx=(0, 12), pady=8)

        _label(top, "Search:", 12).grid(row=0, column=2, padx=(8, 4), pady=10)
        self._pl_search = _entry(top, "Filter by company, stage, priority…", width=280)
        self._pl_search.grid(row=0, column=3, sticky="ew", padx=(0, 12), pady=8)
        self._pl_search.bind("<KeyRelease>", lambda _: self._refresh_pipeline())

        self._pl_count_lbl = _label(top, "0 leads", 11, color=TEXT_SECONDARY)
        self._pl_count_lbl.grid(row=0, column=4, padx=12)

        _btn(top, "📤 Export", self._pipeline_export,
             fg=BG_ELEVATED, hover="#2E3355", width=110).grid(row=0, column=5, padx=8, pady=8)
        _btn(top, "🗑 Delete", self._pipeline_delete,
             fg="#2A1A1A", hover=ACCENT_RED, width=110).grid(row=0, column=6, padx=(0, 12), pady=8)

        # ── Split: table left, detail right ──
        split = ctk.CTkFrame(parent, fg_color=BG_BASE)
        split.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        split.grid_columnconfigure(0, weight=3)
        split.grid_columnconfigure(1, weight=2)
        split.grid_rowconfigure(0, weight=1)

        # Table
        tbl_frame = ctk.CTkFrame(split, fg_color=BG_SURFACE, corner_radius=10)
        tbl_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        tbl_frame.grid_columnconfigure(0, weight=1)
        tbl_frame.grid_rowconfigure(0, weight=1)
        self._build_pipeline_table(tbl_frame)

        # Detail panel
        detail = ctk.CTkFrame(split, fg_color=BG_SURFACE, corner_radius=10)
        detail.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        detail.grid_columnconfigure(0, weight=1)
        self._build_pipeline_detail(detail)

    def _build_pipeline_table(self, parent):
        import tkinter.ttk as ttk
        style = ttk.Style()
        style.configure("Pipeline.Treeview",
                         background=BG_CARD, foreground=TEXT_PRIMARY,
                         fieldbackground=BG_CARD, rowheight=28,
                         borderwidth=0, font=("Segoe UI", 11))
        style.configure("Pipeline.Treeview.Heading",
                         background=BG_ELEVATED, foreground=TEXT_SECONDARY,
                         relief="flat", font=("Segoe UI", 11, "bold"))
        style.map("Pipeline.Treeview",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", "#FFFFFF")])

        cols = ("name", "stage", "priority", "score", "follow_up", "contact", "phone")
        self._pl_tree = ttk.Treeview(parent, columns=cols, show="headings",
                                      style="Pipeline.Treeview")
        hdrs = [("name", "Company", 220), ("stage", "Stage", 110),
                ("priority", "Priority", 85), ("score", "Score", 60),
                ("follow_up", "Follow-Up", 110), ("contact", "Contact", 160),
                ("phone", "Phone", 130)]
        for col, text, w in hdrs:
            self._pl_tree.heading(col, text=text)
            self._pl_tree.column(col, width=w,
                                  anchor="center" if col in ("stage", "priority", "score") else "w")

        self._pl_tree.tag_configure("Won", background="#0D2B1E")
        self._pl_tree.tag_configure("Lost", background="#1C1C1C")
        self._pl_tree.tag_configure("HIGH", background="#2A1515")
        self._pl_tree.tag_configure("MEDIUM", background="#2A2010")

        self._pl_tree.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self._pl_tree.bind("<<TreeviewSelect>>", self._pipeline_on_select)

        sb = ttk.Scrollbar(parent, orient="vertical", command=self._pl_tree.yview)
        sb.grid(row=0, column=1, sticky="ns", pady=8)
        self._pl_tree.configure(yscrollcommand=sb.set)

    def _build_pipeline_detail(self, parent):
        parent.grid_rowconfigure(12, weight=1)

        _label(parent, "Lead CRM Panel", 14, "bold").grid(
            row=0, column=0, padx=16, pady=(16, 4), sticky="w")
        _separator(parent).grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))

        self._pl_name_lbl = _label(parent, "—", 13, "bold", color=ACCENT)
        self._pl_name_lbl.grid(row=2, column=0, padx=16, sticky="w")

        self._pl_addr_lbl = _label(parent, "", 11, color=TEXT_SECONDARY, wraplength=340, justify="left")
        self._pl_addr_lbl.grid(row=3, column=0, padx=16, pady=(2, 10), sticky="w")

        # Stage
        _label(parent, "Pipeline Stage", 11, color=TEXT_SECONDARY).grid(
            row=4, column=0, padx=16, sticky="w")
        self._pl_stage_edit = ctk.CTkOptionMenu(
            parent, values=PIPELINE_STAGES,
            fg_color=BG_ELEVATED, button_color=ACCENT,
            button_hover_color=ACCENT_HOVER, text_color=TEXT_PRIMARY, width=220)
        self._pl_stage_edit.grid(row=5, column=0, padx=16, pady=(2, 8), sticky="w")

        # Contact name + role
        cf = ctk.CTkFrame(parent, fg_color="transparent")
        cf.grid(row=6, column=0, sticky="ew", padx=16, pady=(0, 8))
        cf.grid_columnconfigure(0, weight=1)
        cf.grid_columnconfigure(1, weight=1)
        _label(cf, "Contact Name", 11, color=TEXT_SECONDARY).grid(row=0, column=0, sticky="w")
        _label(cf, "Role / Title", 11, color=TEXT_SECONDARY).grid(row=0, column=1, sticky="w", padx=(8, 0))
        self._pl_contact = _entry(cf, "e.g. Ahmad bin Ismail")
        self._pl_contact.grid(row=1, column=0, sticky="ew")
        self._pl_role = _entry(cf, "e.g. Procurement Manager")
        self._pl_role.grid(row=1, column=1, sticky="ew", padx=(8, 0))

        # Follow-up date
        _label(parent, "Follow-Up Date  (YYYY-MM-DD)", 11, color=TEXT_SECONDARY).grid(
            row=7, column=0, padx=16, pady=(0, 2), sticky="w")
        self._pl_followup = _entry(parent, date.today().isoformat())
        self._pl_followup.grid(row=8, column=0, padx=16, sticky="ew", pady=(0, 8))

        # Notes
        _label(parent, "Notes", 11, color=TEXT_SECONDARY).grid(
            row=9, column=0, padx=16, sticky="w")
        self._pl_notes = ctk.CTkTextbox(parent, height=110, wrap="word",
                                         fg_color=BG_ELEVATED, text_color=TEXT_PRIMARY,
                                         corner_radius=6, font=ctk.CTkFont(size=12))
        self._pl_notes.grid(row=10, column=0, padx=16, sticky="ew", pady=(2, 10))

        # Action buttons
        btn_row = ctk.CTkFrame(parent, fg_color="transparent")
        btn_row.grid(row=11, column=0, padx=16, sticky="ew", pady=(0, 8))

        _btn(btn_row, "💾 Save Changes", self._pipeline_save_crm,
             fg=ACCENT_GREEN, hover="#0EA271", width=160).pack(side="left", padx=(0, 6))
        _btn(btn_row, "👤 LinkedIn", self._pipeline_open_linkedin,
             fg="#0A66C2", hover="#004182", width=110).pack(side="left", padx=(0, 6))
        _btn(btn_row, "💬 Copy WA", self._pipeline_copy_wa,
             fg="#25D366", hover="#1DB954", width=110).pack(side="left")

        # AI brief box
        _label(parent, "AI Sales Brief", 11, color=TEXT_SECONDARY).grid(
            row=12, column=0, padx=16, pady=(4, 2), sticky="w")
        self._pl_brief = ctk.CTkTextbox(parent, height=160, wrap="word",
                                         fg_color=BG_CARD, text_color=TEXT_SECONDARY,
                                         corner_radius=6, font=ctk.CTkFont(size=11))
        self._pl_brief.grid(row=13, column=0, padx=16, sticky="nsew", pady=(0, 16))

    # ── Pipeline actions ──────────────────────────────────────────────────────

    def _refresh_pipeline(self):
        stage = self._pl_stage_var.get() if hasattr(self, "_pl_stage_var") else "All"
        q = self._pl_search.get().strip().lower() if hasattr(self, "_pl_search") else ""
        if stage == "All":
            leads = db.get_all_leads()
        else:
            leads = db.get_leads_by_stage(stage)
        if q:
            leads = [l for l in leads if q in " ".join(str(v).lower() for v in l.values())]
        self._pipeline_leads = leads

        for item in self._pl_tree.get_children():
            self._pl_tree.delete(item)

        for lead in leads:
            tag = lead.get("stage", "") if lead.get("stage") in ("Won", "Lost") else lead.get("priority", "")
            self._pl_tree.insert("", "end", iid=str(lead["id"]), tags=(tag,), values=(
                lead.get("name", ""),
                lead.get("stage", "New"),
                lead.get("priority", ""),
                lead.get("lead_score", ""),
                lead.get("follow_up_date", ""),
                lead.get("contact_name", ""),
                lead.get("phone", ""),
            ))
        self._pl_count_lbl.configure(text=f"{len(leads)} leads")

    def _pipeline_on_select(self, _=None):
        sel = self._pl_tree.selection()
        if not sel:
            return
        lead_id = int(sel[0])
        lead = next((l for l in self._pipeline_leads if l["id"] == lead_id), None)
        if not lead:
            return
        self._selected_pipeline = lead

        self._pl_name_lbl.configure(text=lead.get("name", ""))
        self._pl_addr_lbl.configure(text=lead.get("address", ""))
        self._pl_stage_edit.set(lead.get("stage", "New"))

        self._pl_contact.delete(0, "end")
        self._pl_contact.insert(0, lead.get("contact_name", ""))
        self._pl_role.delete(0, "end")
        self._pl_role.insert(0, lead.get("contact_role", ""))
        self._pl_followup.delete(0, "end")
        self._pl_followup.insert(0, lead.get("follow_up_date", ""))
        self._pl_notes.delete("1.0", "end")
        self._pl_notes.insert("1.0", lead.get("notes", ""))

        # AI brief
        brief = "\n".join(filter(None, [
            f"Score: {lead.get('lead_score','')} / 100  |  Priority: {lead.get('priority','')}",
            f"Potential: {lead.get('logistics_potential','')}",
            f"Service: {lead.get('suggested_service','')}",
            f"Pain Points: {lead.get('possible_pain_points','')}",
            "",
            f"Opening: {lead.get('sales_opening_line','')}",
            "",
            f"WhatsApp:\n{lead.get('whatsapp_draft','')}",
            "",
            f"Email Subject: {lead.get('email_subject','')}",
            f"\n{lead.get('email_body','')}",
        ]))
        self._pl_brief.configure(state="normal")
        self._pl_brief.delete("1.0", "end")
        self._pl_brief.insert("1.0", brief or "No AI analysis yet.")
        self._pl_brief.configure(state="disabled")

    def _pipeline_save_crm(self):
        lead = self._selected_pipeline
        if not lead:
            messagebox.showinfo("No Lead Selected", "Select a lead first.")
            return
        db.update_lead_crm(
            lead["id"],
            stage=self._pl_stage_edit.get(),
            contact_name=self._pl_contact.get().strip(),
            contact_role=self._pl_role.get().strip(),
            follow_up_date=self._pl_followup.get().strip(),
            notes=self._pl_notes.get("1.0", "end").strip(),
        )
        db.log_activity(lead["id"], f"Stage → {self._pl_stage_edit.get()}", self._pl_notes.get("1.0", "end").strip()[:120])
        self._refresh_pipeline()
        self._refresh_followups()
        self._refresh_analytics()
        messagebox.showinfo("Saved", "CRM record updated.")

    def _pipeline_delete(self):
        lead = self._selected_pipeline
        if not lead:
            return
        if messagebox.askyesno("Delete Lead", f"Permanently delete '{lead.get('name','')}'?"):
            db.delete_lead(lead["id"])
            self._selected_pipeline = None
            self._refresh_pipeline()
            self._refresh_analytics()

    def _pipeline_export(self):
        leads = self._pipeline_leads
        if not leads:
            messagebox.showinfo("No Leads", "No leads to export.")
            return
        path = filedialog.asksaveasfilename(
            title="Export Pipeline", defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")], initialfile="Pipeline_Export.xlsx")
        if not path:
            return
        try:
            export_leads_to_excel(leads, Path(path))
            messagebox.showinfo("Exported", f"Saved to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    def _pipeline_open_linkedin(self):
        lead = self._selected_pipeline
        if not lead:
            return
        company = lead.get("name", "").strip()
        role = self._pl_role.get().strip() or "Supply Chain Manager"
        q = urllib.parse.quote(f"{company} {role}")
        webbrowser.open(f"https://www.linkedin.com/search/results/people/?keywords={q}")

    def _pipeline_copy_wa(self):
        lead = self._selected_pipeline
        if not lead:
            return
        msg = lead.get("whatsapp_draft", "")
        if not msg:
            messagebox.showinfo("No Draft", "No WhatsApp draft available — run AI analysis first.")
            return
        self.clipboard_clear()
        self.clipboard_append(msg)
        messagebox.showinfo("Copied", "WhatsApp message copied!")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — FOLLOW-UPS
    # ══════════════════════════════════════════════════════════════════════════

    def _build_followup_tab(self, parent):
        parent.configure(fg_color=BG_BASE)
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        # Top
        top = ctk.CTkFrame(parent, fg_color=BG_SURFACE, corner_radius=10)
        top.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))

        _label(top, "📅  Today's Follow-Ups & Overdue", 15, "bold").pack(side="left", padx=16, pady=12)
        self._fu_count_lbl = _label(top, "", 12, color=ACCENT_AMBER)
        self._fu_count_lbl.pack(side="left", padx=8)

        _btn(top, "🔄  Refresh", self._refresh_followups,
             fg=BG_ELEVATED, hover="#2E3355", width=110).pack(side="right", padx=12, pady=8)

        # Split
        split = ctk.CTkFrame(parent, fg_color=BG_BASE)
        split.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        split.grid_columnconfigure(0, weight=2)
        split.grid_columnconfigure(1, weight=3)
        split.grid_rowconfigure(0, weight=1)

        # List
        list_frame = ctk.CTkFrame(split, fg_color=BG_SURFACE, corner_radius=10)
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(1, weight=1)

        _label(list_frame, "Due / Overdue Leads", 13, "bold").grid(
            row=0, column=0, padx=16, pady=(12, 6), sticky="w")

        self._fu_listbox = ctk.CTkScrollableFrame(list_frame, fg_color=BG_CARD, corner_radius=8)
        self._fu_listbox.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self._fu_listbox.grid_columnconfigure(0, weight=1)

        # Action panel
        action = ctk.CTkFrame(split, fg_color=BG_SURFACE, corner_radius=10)
        action.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        action.grid_columnconfigure(0, weight=1)
        self._build_followup_actions(action)

    def _build_followup_actions(self, parent):
        _label(parent, "Quick Actions", 14, "bold").grid(
            row=0, column=0, padx=16, pady=(16, 4), sticky="w")
        _separator(parent).grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))

        self._fu_name_lbl = _label(parent, "Select a lead", 13, "bold", color=ACCENT)
        self._fu_name_lbl.grid(row=2, column=0, padx=16, sticky="w")

        self._fu_due_lbl = _label(parent, "", 11, color=ACCENT_AMBER)
        self._fu_due_lbl.grid(row=3, column=0, padx=16, pady=(2, 12), sticky="w")

        # Stage quick-set
        _label(parent, "Move to Stage", 11, color=TEXT_SECONDARY).grid(
            row=4, column=0, padx=16, sticky="w")
        self._fu_stage_var = ctk.StringVar(value="Contacted")
        stage_row = ctk.CTkFrame(parent, fg_color="transparent")
        stage_row.grid(row=5, column=0, padx=16, pady=(4, 12), sticky="w")
        for s in PIPELINE_STAGES:
            color = STAGE_COLORS.get(s, BG_ELEVATED)
            ctk.CTkRadioButton(
                stage_row, text=s, variable=self._fu_stage_var, value=s,
                fg_color=color, hover_color=color, text_color=TEXT_PRIMARY,
                font=ctk.CTkFont(size=11),
            ).pack(side="left", padx=(0, 10))

        # Reschedule
        _label(parent, "Reschedule Follow-Up  (YYYY-MM-DD)", 11, color=TEXT_SECONDARY).grid(
            row=6, column=0, padx=16, sticky="w")
        self._fu_new_date = _entry(parent, date.today().isoformat())
        self._fu_new_date.grid(row=7, column=0, padx=16, sticky="ew", pady=(4, 12))

        # Quick note
        _label(parent, "Quick Note", 11, color=TEXT_SECONDARY).grid(
            row=8, column=0, padx=16, sticky="w")
        self._fu_note = ctk.CTkTextbox(parent, height=100, wrap="word",
                                        fg_color=BG_ELEVATED, text_color=TEXT_PRIMARY,
                                        corner_radius=6, font=ctk.CTkFont(size=12))
        self._fu_note.grid(row=9, column=0, padx=16, sticky="ew", pady=(4, 12))

        # Buttons
        btns = ctk.CTkFrame(parent, fg_color="transparent")
        btns.grid(row=10, column=0, padx=16, sticky="ew", pady=(0, 12))

        _btn(btns, "✅  Mark & Move Stage", self._followup_mark,
             fg=ACCENT_GREEN, hover="#0EA271", width=190).pack(side="left", padx=(0, 8))
        _btn(btns, "📅  Reschedule Only", self._followup_reschedule,
             fg=ACCENT_AMBER, hover="#D97706", width=165).pack(side="left")

        _btn(parent, "🗑  Archive (Mark Lost)", self._followup_archive,
             fg="#2A1A1A", hover=ACCENT_RED, width=200).grid(
            row=11, column=0, padx=16, sticky="w", pady=(0, 16))

        # Activity log
        _separator(parent).grid(row=12, column=0, sticky="ew", padx=12, pady=(0, 8))
        _label(parent, "Activity History", 12, "bold").grid(
            row=13, column=0, padx=16, sticky="w")
        self._fu_activity = ctk.CTkTextbox(parent, height=160, wrap="word",
                                            fg_color=BG_CARD, text_color=TEXT_SECONDARY,
                                            corner_radius=6, font=ctk.CTkFont(size=11))
        self._fu_activity.grid(row=14, column=0, padx=16, sticky="ew", pady=(4, 16))

    # ── Follow-up actions ─────────────────────────────────────────────────────

    def _refresh_followups(self):
        self._fu_leads = db.get_followups_due()
        # Clear
        for w in self._fu_listbox.winfo_children():
            w.destroy()

        if not self._fu_leads:
            _label(self._fu_listbox, "No follow-ups due today 🎉", 12,
                   color=TEXT_SECONDARY).grid(row=0, column=0, padx=16, pady=20)
            self._fu_count_lbl.configure(text="All clear!")
            return

        self._fu_count_lbl.configure(text=f"{len(self._fu_leads)} due / overdue")
        today = date.today().isoformat()

        for i, lead in enumerate(self._fu_leads):
            fu_date = lead.get("follow_up_date", "")
            is_overdue = fu_date and fu_date < today
            bg = "#2A1515" if is_overdue else BG_ELEVATED

            card = ctk.CTkFrame(self._fu_listbox, fg_color=bg, corner_radius=8)
            card.grid(row=i, column=0, sticky="ew", padx=4, pady=4)
            card.grid_columnconfigure(0, weight=1)

            _label(card, lead.get("name", ""), 12, "bold").grid(
                row=0, column=0, padx=12, pady=(8, 2), sticky="w")
            tag_txt = f"{'⚠ OVERDUE' if is_overdue else '📅 Due'}  {fu_date}  ·  {lead.get('stage','')}"
            tag_color = ACCENT_RED if is_overdue else ACCENT_AMBER
            _label(card, tag_txt, 10, color=tag_color).grid(
                row=1, column=0, padx=12, pady=(0, 6), sticky="w")

            card.bind("<Button-1>", lambda e, l=lead: self._followup_select(l))
            for child in card.winfo_children():
                child.bind("<Button-1>", lambda e, l=lead: self._followup_select(l))

    def _followup_select(self, lead):
        self._selected_pipeline = lead
        self._fu_name_lbl.configure(text=lead.get("name", ""))
        fu = lead.get("follow_up_date", "")
        today = date.today().isoformat()
        status = "⚠ OVERDUE" if (fu and fu < today) else f"Due: {fu}"
        self._fu_due_lbl.configure(text=status)
        self._fu_new_date.delete(0, "end")
        self._fu_new_date.insert(0, date.today().isoformat())
        self._fu_note.delete("1.0", "end")

        activities = db.get_activities(lead["id"])
        log = "\n".join(
            f"[{a['created_at'][:16]}]  {a['action']}" +
            (f"  —  {a['note']}" if a.get("note") else "")
            for a in activities
        ) or "No activity yet."
        self._fu_activity.configure(state="normal")
        self._fu_activity.delete("1.0", "end")
        self._fu_activity.insert("1.0", log)
        self._fu_activity.configure(state="disabled")

    def _followup_mark(self):
        lead = self._selected_pipeline
        if not lead:
            messagebox.showinfo("No Lead", "Select a lead from the list.")
            return
        new_stage = self._fu_stage_var.get()
        note = self._fu_note.get("1.0", "end").strip()
        new_date = self._fu_new_date.get().strip()
        db.update_lead_crm(lead["id"], stage=new_stage,
                           last_contacted=date.today().isoformat(),
                           follow_up_date=new_date, notes=note)
        db.log_activity(lead["id"], f"Followed up → {new_stage}", note[:120])
        self._refresh_followups()
        self._refresh_pipeline()
        self._refresh_analytics()

    def _followup_reschedule(self):
        lead = self._selected_pipeline
        if not lead:
            return
        new_date = self._fu_new_date.get().strip()
        if not new_date:
            messagebox.showwarning("No Date", "Enter a reschedule date.")
            return
        db.update_lead_crm(lead["id"], follow_up_date=new_date)
        db.log_activity(lead["id"], f"Rescheduled to {new_date}")
        self._refresh_followups()
        self._refresh_pipeline()

    def _followup_archive(self):
        lead = self._selected_pipeline
        if not lead:
            return
        if messagebox.askyesno("Archive Lead", f"Mark '{lead.get('name','')}' as Lost?"):
            db.update_lead_crm(lead["id"], stage="Lost", follow_up_date="")
            db.log_activity(lead["id"], "Archived → Lost")
            self._refresh_followups()
            self._refresh_pipeline()
            self._refresh_analytics()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 4 — ANALYTICS
    # ══════════════════════════════════════════════════════════════════════════

    def _build_analytics_tab(self, parent):
        parent.configure(fg_color=BG_BASE)
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        # Top full-width KPI strip
        kpi_strip = ctk.CTkFrame(parent, fg_color=BG_SURFACE, corner_radius=10)
        kpi_strip.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=(12, 6))
        for i in range(5):
            kpi_strip.grid_columnconfigure(i, weight=1)

        self._kpi_labels: dict[str, ctk.CTkLabel] = {}
        kpis = [
            ("total",       "Total Leads",    "🏢"),
            ("avg_score",   "Avg AI Score",   "🤖"),
            ("won",         "Won",            "🏆"),
            ("overdue",     "Overdue",        "⚠️"),
            ("pipeline",    "In Pipeline",    "📋"),
        ]
        for i, (key, title, icon) in enumerate(kpis):
            card = ctk.CTkFrame(kpi_strip, fg_color=BG_ELEVATED, corner_radius=8)
            card.grid(row=0, column=i, padx=10, pady=10, sticky="ew")
            _label(card, f"{icon}  {title}", 11, color=TEXT_SECONDARY).pack(pady=(10, 2))
            lbl = _label(card, "—", 28, "bold", color=ACCENT)
            lbl.pack(pady=(0, 10))
            self._kpi_labels[key] = lbl

        # Pipeline breakdown
        pipe_frame = ctk.CTkFrame(parent, fg_color=BG_SURFACE, corner_radius=10)
        pipe_frame.grid(row=1, column=0, sticky="nsew", padx=(12, 6), pady=(0, 12))
        pipe_frame.grid_columnconfigure(0, weight=1)

        _label(pipe_frame, "Pipeline Stage Breakdown", 14, "bold").grid(
            row=0, column=0, padx=16, pady=(16, 8), sticky="w")

        self._analytics_stage_frame = ctk.CTkScrollableFrame(
            pipe_frame, fg_color="transparent")
        self._analytics_stage_frame.grid(row=1, column=0, sticky="nsew",
                                          padx=8, pady=(0, 8))
        self._analytics_stage_frame.grid_columnconfigure(0, weight=1)
        pipe_frame.grid_rowconfigure(1, weight=1)

        # Right panel
        right = ctk.CTkFrame(parent, fg_color=BG_BASE)
        right.grid(row=1, column=1, sticky="nsew", padx=(6, 12), pady=(0, 12))
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        # Priority breakdown
        pri_frame = ctk.CTkFrame(right, fg_color=BG_SURFACE, corner_radius=10)
        pri_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 6))
        pri_frame.grid_columnconfigure(0, weight=1)

        _label(pri_frame, "Priority Breakdown", 14, "bold").grid(
            row=0, column=0, padx=16, pady=(16, 8), sticky="w")
        self._analytics_pri_frame = ctk.CTkScrollableFrame(
            pri_frame, fg_color="transparent")
        self._analytics_pri_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self._analytics_pri_frame.grid_columnconfigure(0, weight=1)
        pri_frame.grid_rowconfigure(1, weight=1)

        # Top leads
        top_frame = ctk.CTkFrame(right, fg_color=BG_SURFACE, corner_radius=10)
        top_frame.grid(row=1, column=0, sticky="nsew", pady=(6, 0))
        top_frame.grid_columnconfigure(0, weight=1)

        _label(top_frame, "🏆  Top Leads by AI Score", 14, "bold").grid(
            row=0, column=0, padx=16, pady=(16, 8), sticky="w")
        self._analytics_top_frame = ctk.CTkScrollableFrame(
            top_frame, fg_color="transparent")
        self._analytics_top_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self._analytics_top_frame.grid_columnconfigure(0, weight=1)
        top_frame.grid_rowconfigure(1, weight=1)

        # Refresh btn
        _btn(parent, "🔄  Refresh Analytics", self._refresh_analytics,
             fg=BG_ELEVATED, hover="#2E3355", width=200).grid(
            row=2, column=0, columnspan=2, padx=12, pady=(0, 12))

    # ── Analytics refresh ─────────────────────────────────────────────────────

    def _refresh_analytics(self):
        data = db.get_analytics()
        overdue_count = len(db.get_followups_due())
        in_pipeline = sum(v for k, v in data["by_stage"].items() if k not in ("Won", "Lost"))

        self._kpi_labels["total"].configure(text=str(data["total"]))
        self._kpi_labels["avg_score"].configure(text=str(data["avg_score"]))
        self._kpi_labels["won"].configure(text=str(data["by_stage"].get("Won", 0)))
        self._kpi_labels["overdue"].configure(text=str(overdue_count))
        self._kpi_labels["pipeline"].configure(text=str(in_pipeline))

        # Stage bars
        for w in self._analytics_stage_frame.winfo_children():
            w.destroy()
        total = max(data["total"], 1)
        for i, stage in enumerate(PIPELINE_STAGES):
            count = data["by_stage"].get(stage, 0)
            pct = count / total
            color = STAGE_COLORS.get(stage, ACCENT)
            row = ctk.CTkFrame(self._analytics_stage_frame, fg_color="transparent")
            row.grid(row=i, column=0, sticky="ew", pady=3)
            row.grid_columnconfigure(1, weight=1)
            _label(row, f"{stage:<12}", 12, color=TEXT_SECONDARY).grid(row=0, column=0, padx=(4, 8))
            bar_bg = ctk.CTkFrame(row, fg_color=BG_ELEVATED, corner_radius=4, height=20)
            bar_bg.grid(row=0, column=1, sticky="ew")
            bar_bg.grid_columnconfigure(0, weight=1)
            if pct > 0:
                bar_fill = ctk.CTkFrame(bar_bg, fg_color=color, corner_radius=4, height=20)
                bar_fill.place(relx=0, rely=0, relwidth=pct, relheight=1)
            _label(row, f"{count}", 12, "bold", color=color).grid(row=0, column=2, padx=(8, 4))

        # Priority bars
        for w in self._analytics_pri_frame.winfo_children():
            w.destroy()
        for i, (pri, color) in enumerate([("HIGH", ACCENT_RED), ("MEDIUM", ACCENT_AMBER), ("LOW", TEXT_DIM)]):
            count = data["by_priority"].get(pri, 0)
            pct = count / total
            row = ctk.CTkFrame(self._analytics_pri_frame, fg_color="transparent")
            row.grid(row=i, column=0, sticky="ew", pady=3)
            row.grid_columnconfigure(1, weight=1)
            _label(row, f"{pri:<8}", 12, color=color).grid(row=0, column=0, padx=(4, 8))
            bar_bg = ctk.CTkFrame(row, fg_color=BG_ELEVATED, corner_radius=4, height=20)
            bar_bg.grid(row=0, column=1, sticky="ew")
            if pct > 0:
                bar_fill = ctk.CTkFrame(bar_bg, fg_color=color, corner_radius=4, height=20)
                bar_fill.place(relx=0, rely=0, relwidth=pct, relheight=1)
            _label(row, f"{count}", 12, "bold", color=color).grid(row=0, column=2, padx=(8, 4))

        # Top leads list
        for w in self._analytics_top_frame.winfo_children():
            w.destroy()
        for i, lead in enumerate(data["top_leads"]):
            pri_color = PRIORITY_COLORS.get(lead.get("priority", ""), TEXT_DIM)
            stage_color = STAGE_COLORS.get(lead.get("stage", ""), TEXT_DIM)
            card = ctk.CTkFrame(self._analytics_top_frame, fg_color=BG_ELEVATED, corner_radius=6)
            card.grid(row=i, column=0, sticky="ew", pady=3, padx=4)
            card.grid_columnconfigure(1, weight=1)
            _label(card, f"#{i+1}", 12, "bold", color=TEXT_DIM).grid(row=0, column=0, padx=(10, 6), pady=8)
            _label(card, lead.get("name",""), 12, "bold").grid(row=0, column=1, sticky="w", pady=8)
            _label(card, f"{lead.get('lead_score','')} pts", 12, "bold", color=ACCENT).grid(row=0, column=2, padx=8)
            _label(card, lead.get("priority",""), 10, color=pri_color).grid(row=0, column=3, padx=(0,4))
            _label(card, lead.get("stage",""), 10, color=stage_color).grid(row=0, column=4, padx=(0,10))


# ── Entry point ───────────────────────────────────────────────────────────────

def run_app():
    app = AILeadFinderApp()
    app.mainloop()
