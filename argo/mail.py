"""mail.py -- the part of a reply that is Ben's own words: everything above the quoted email.

A reply to the statement or bounty email lands on the issue as a comment, and GitHub keeps the
quoted email under it unless the client set it apart. On 16/11/2026 his phone glued its header
to the word itself -- `paidOn 16 Nov 2026 06:27, "github-actions[bot]" ... wrote:...` -- so the
first word read as "paidon" and the week stayed unpaid. `own_words` cuts at the header wherever
it starts, glued or on its own line; `reply.py` and `bounty.py` both read through it.

    python -m argo.mail --selftest
"""
import re

_DAY = r"(?:\d|Mon|Tue|Wed|Thu|Fri|Sat|Sun|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
QUOTE_HEADER = re.compile(
    r"^[ \t]*On [^\n]*wrote:[ \t]*\r?$"           # "On <anything> wrote:" alone on its line
    rf"|On\s{_DAY}.{{0,300}}?wrote:"               # the same with a date, glued to the reply or wrapped
    r"|^[ \t]*-{2,}\s*Original Message\s*-{2,}"    # Outlook desktop
    r"|^[ \t]*_{10,}[ \t]*\r?$"                    # Outlook's rule above its From/Sent block
    r"|From:\s.{0,300}?\bSent:",                   # that block, even glued to the reply
    re.M | re.S)


def own_words(text: str) -> str:
    """The comment up to the quoted email (the whole comment when there is none)."""
    text = text or ""
    m = QUOTE_HEADER.search(text)
    return text[:m.start()] if m else text


def selftest() -> None:
    glued = ('paidOn 16 Nov 2026 06:27, "github-actions[bot]" ***@***.***> wrote:github-actions[bot] '
             'created an issue (LoneWonderer1976/argo#17)\r\n\r\n2 activities · 15.1 points · £3.76')
    assert own_words(glued) == "paid"                                    # the 16/11 reply, as it arrived
    assert own_words("paid all\r\n\r\nOn Mon, 16 Nov 2026 at 06:27, github-actions[bot] <\r\n"
                     "notifications@github.com> wrote:\r\n> 2 activities").strip() == "paid all"
    assert own_words("approve\nOn Sunday the bot wrote:\n> x").strip() == "approve"
    assert own_words("paid cash\r\n\r\n________________________________\r\nFrom: github-actions[bot]"
                     " <n@github.com>\r\nSent: 16 November 2026 06:27").strip() == "paid cash"
    assert own_words("paidFrom: github-actions[bot] <n@github.com>\r\nSent: Monday") == "paid"
    assert own_words("paid\n-----Original Message-----\nFrom: x").strip() == "paid"
    for kept in ("strike 25077194822 On a lift with Mum", "strike 1 From: the car park",
                 "set week_cap_points 40", "approve\nreward x2", "", "paid"):
        assert own_words(kept) == kept, kept                              # ordinary words are never cut
    assert own_words(None) == ""
    print("mail: selftest OK")


if __name__ == "__main__":
    selftest()
