#!/usr/bin/env python3
"""Render stable README visual-envelope chrome for one approved season.

Section labels are stored as vector outlines so README rendering does not depend on
client-installed Japanese fonts.
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
ROOT = LAB.parent
MANIFEST = LAB / "theme-manifest.json"

LABEL_OUTLINES = {
    "プロジェクト": """<g transform="translate(374.000 43) scale(0.02200 -0.02200)" fill="#eef1f4">
  <path transform="translate(0.000 0)" d="M804 733C804 765 830 791 862 791C893 791 919 765 919 733C919 702 893 676 862 676C830 676 804 702 804 733ZM742 733 744 714C723 711 701 710 687 710C630 710 299 710 224 710C191 710 134 714 105 718V577C130 579 178 581 224 581C299 581 629 581 689 581C676 495 638 382 572 299C491 197 378 110 180 64L289 -56C467 2 600 101 691 221C775 332 818 487 841 585L849 615L862 614C927 614 981 668 981 733C981 799 927 853 862 853C796 853 742 799 742 733Z"/>
  <path transform="translate(1181.818 0)" d="M126 709C128 681 128 640 128 612C128 554 128 183 128 123C128 75 125 -12 125 -17H263L262 37H744L743 -17H881C881 -13 879 83 879 122C879 182 879 551 879 612C879 642 879 679 881 709C845 707 807 707 782 707C710 707 304 707 232 707C205 707 167 708 126 709ZM262 165V580H745V165Z"/>
  <path transform="translate(2363.636 0)" d="M730 768 646 733C682 682 705 639 734 576L821 613C798 659 758 726 730 768ZM867 816 782 781C819 731 844 692 876 629L961 667C937 711 898 776 867 816ZM295 787 223 677C289 640 393 573 449 534L523 644C471 680 361 751 295 787ZM110 77 185 -54C273 -38 417 12 519 69C682 164 824 290 916 429L839 565C760 422 620 285 450 190C342 130 222 96 110 77ZM141 559 69 449C136 413 240 346 297 306L370 418C319 454 209 523 141 559Z"/>
  <path transform="translate(3545.455 0)" d="M146 104V-27C173 -23 204 -22 228 -22H781C798 -22 835 -23 856 -27V104C836 102 808 98 781 98H563V420H734C757 420 787 418 812 416V542C788 539 758 537 734 537H276C254 537 219 538 197 542V416C219 418 255 420 276 420H432V98H228C203 98 172 101 146 104Z"/>
  <path transform="translate(4727.273 0)" d="M573 780 427 828C418 794 397 748 382 723C332 637 245 508 70 401L182 318C280 385 367 473 434 560H715C699 485 641 365 573 287C486 188 374 101 170 40L288 -66C476 8 597 100 692 216C782 328 839 461 866 550C874 575 888 603 899 622L797 685C774 678 741 673 710 673H509L512 678C524 700 550 745 573 780Z"/>
  <path transform="translate(5909.091 0)" d="M314 96C314 56 310 -4 304 -44H460C456 -3 451 67 451 96V379C559 342 709 284 812 230L869 368C777 413 585 484 451 523V671C451 712 456 756 460 791H304C311 756 314 706 314 671C314 586 314 172 314 96Z"/>
</g>""",
    "活動": """<g transform="translate(426.000 43) scale(0.02200 -0.02200)" fill="#eef1f4">
  <path transform="translate(0.000 0)" d="M83 750C141 717 226 669 266 640L337 737C294 764 207 809 151 837ZM35 473C95 442 181 394 222 365L289 465C245 492 156 536 100 562ZM50 3 151 -78C212 20 275 134 328 239L240 319C180 203 103 78 50 3ZM330 558V444H597V316H392V-89H502V-48H802V-84H917V316H711V444H967V558H711V696C790 712 865 732 929 756L837 850C726 805 538 772 368 755C381 729 397 682 402 653C465 659 531 666 597 676V558ZM502 61V207H802V61Z"/>
  <path transform="translate(1181.818 0)" d="M631 833 630 623H536V678H343V728C408 735 471 744 524 755L472 844C361 820 188 803 38 796C49 772 61 735 65 710C119 711 176 714 234 718V678H36V592H234V553H62V242H234V203H58V118H234V59L30 44L44 -57C154 -47 298 -33 443 -17C469 -39 499 -73 514 -97C682 36 728 244 741 513H831C825 190 815 67 795 39C785 26 776 22 760 22C741 22 703 22 660 26C679 -6 692 -55 694 -88C742 -89 788 -89 819 -84C852 -77 876 -67 898 -33C930 12 938 159 948 570C948 584 948 623 948 623H744L746 833ZM343 118H525V203H343V242H520V553H343V592H535V513H627C620 334 596 191 518 82L343 67ZM157 362H234V317H157ZM343 362H421V317H343ZM157 478H234V433H157ZM343 478H421V433H343Z"/>
</g>""",
}


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def label_outline(label: str) -> str:
    try:
        return LABEL_OUTLINES[label]
    except KeyError as exc:
        raise ValueError(f"no vector outline registered for section label: {label}") from exc


def motif_svg(kind: str, accent: str, accent2: str) -> str:
    if kind == "petal":
        return f'''<g fill="{esc(accent)}" opacity=".48">
  <path d="M0,-5 C4,-6 7,-2 5,2 C3,6 -2,7 -5,4 C-7,1 -5,-4 0,-5Z" transform="translate(760 23) rotate(18)"/>
  <path d="M0,-5 C4,-6 7,-2 5,2 C3,6 -2,7 -5,4 C-7,1 -5,-4 0,-5Z" transform="translate(788 17) rotate(-28) scale(.72)"/>
</g>'''
    if kind == "water":
        return f'''<g fill="none" stroke-linecap="round">
  <path d="M704 29 C748 11 796 39 842 20" stroke="{esc(accent)}" stroke-opacity=".34" stroke-width="2"/>
  <path d="M723 35 C764 22 806 42 858 27" stroke="{esc(accent2)}" stroke-opacity=".22" stroke-width="1"/>
</g>'''
    if kind == "leaf":
        return f'''<g fill="{esc(accent)}" opacity=".46">
  <path d="M0,-8 3,-3 8,-5 5,0 10,2 4,4 6,9 1,5 -2,10 -3,5 -9,6 -5,1 -9,-2 -4,-3 -4,-8 0,-4Z" transform="translate(782 23) rotate(16)"/>
  <path d="M0,-8 3,-3 8,-5 5,0 10,2 4,4 6,9 1,5 -2,10 -3,5 -9,6 -5,1 -9,-2 -4,-3 -4,-8 0,-4Z" transform="translate(820 18) rotate(-20) scale(.72)"/>
</g>'''
    if kind == "snow":
        return f'''<g fill="{esc(accent2)}" opacity=".48">
  <circle cx="772" cy="17" r="2"/><circle cx="803" cy="29" r="1.5"/><circle cx="835" cy="16" r="1.2"/>
</g>'''
    raise ValueError(f"unknown motif: {kind}")


def background_defs(bg0: str, bg1: str) -> str:
    return f'''<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="0"><stop stop-color="{esc(bg0)}"/><stop offset=".52" stop-color="{esc(bg1)}"/><stop offset="1" stop-color="{esc(bg0)}"/></linearGradient></defs>'''


def section_band(cfg: dict, label: str, aria: str) -> str:
    c = cfg["chrome"]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="68" viewBox="0 0 900 68" role="img" aria-label="{esc(aria)}">
  {background_defs(c['bg0'], c['bg1'])}
  <rect width="900" height="68" rx="14" fill="url(#bg)"/>
  <path d="M56 34 H318 M582 34 H844" stroke="#eef2f6" stroke-opacity=".10"/>
  <circle cx="336" cy="34" r="2.5" fill="{esc(cfg['accent'])}"/>
  <circle cx="564" cy="34" r="2.5" fill="{esc(c['accent2'])}"/>
  {label_outline(label)}
  {motif_svg(c['motif'], cfg['accent'], c['accent2'])}
</svg>'''


def footer(cfg: dict) -> str:
    c = cfg["chrome"]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="92" viewBox="0 0 900 92" role="img" aria-label="季節ダークプロフィール終端">
  {background_defs(c['bg0'], c['bg1'])}
  <rect width="900" height="92" rx="16" fill="url(#bg)"/>
  <path d="M0 68 C132 46 236 82 356 63 C482 43 582 77 704 53 C788 37 842 42 900 29" fill="none" stroke="{esc(cfg['accent'])}" stroke-opacity=".08" stroke-width="15"/>
  <path d="M322 46 H420 M480 46 H578" stroke="#eef2f6" stroke-opacity=".14"/>
  <circle cx="450" cy="46" r="3" fill="{esc(cfg['accent'])}"/><circle cx="450" cy="46" r="10" fill="none" stroke="{esc(c['accent2'])}" stroke-opacity=".24"/>
  {motif_svg(c['motif'], cfg['accent'], c['accent2'])}
</svg>'''


def render(season: str, out_root: Path = ROOT) -> list[Path]:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    cfg = data["seasons"][season]
    assets = data["live_assets"]
    outputs = {
        "projects": section_band(cfg, "プロジェクト", "プロジェクト セクション"),
        "activity": section_band(cfg, "活動", "活動 セクション"),
        "footer": footer(cfg),
    }
    written: list[Path] = []
    for key, content in outputs.items():
        path = out_root / assets[key]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content + "\n", encoding="utf-8")
        written.append(path)
    return written


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", required=True, choices=["spring", "summer", "autumn", "winter"])
    args = parser.parse_args()
    for path in render(args.season):
        print(path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
