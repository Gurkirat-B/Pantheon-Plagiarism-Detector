import re
from dataclasses import dataclass

@dataclass(frozen=True)
class Token:
    text: str
    line: int

_re_ws  = re.compile(r"[ \t\r]+")
_re_id  = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_re_num = re.compile(r"\d+(\.\d+)?")
_re_str = re.compile(r'"([^"\\]|\\.)*"')
_re_chr = re.compile(r"'([^'\\]|\\.)*'")

OPS = sorted({
    "==","!=",">=","<=","&&","||","++","--","+=","-=","*=","/=","%=",
    "->","::","<<",">>","&","|","^","~","!","+","-","*","/","%","=",
    ">","<","?",":",".",",",";","(",")","{","}","[","]"
}, key=len, reverse=True)

JAVA_KW = {
  "class","public","private","protected","static","void","int","double","float",
  "boolean","char","new","return","if","else","for","while","do","switch",
  "case","break","continue","this","null","true","false","try","catch","finally",
  "throw","throws","import","package","extends","implements","interface"
}

C_KW = {
  "int","char","float","double","void","return","if","else","for","while","do",
  "switch","case","break","continue","struct","typedef","enum","static","const",
  "unsigned","signed","long","short","sizeof"
}

def tokenize(text: str, lang: str = "java", normalize_ids: bool = True, normalize_literals: bool = True):
    kws = JAVA_KW if lang == "java" else C_KW
    tokens = []
    i, n, line = 0, len(text), 1

    def add(t):
        tokens.append(Token(text=t, line=line))

    while i < n:
        ch = text[i]

        if ch == "\n":
            line += 1
            i += 1
            continue

        if ch in " \t\r":
            m = _re_ws.match(text, i)
            i = m.end()
            continue

        m = _re_str.match(text, i)
        if m:
            add("STR" if normalize_literals else m.group(0))
            i = m.end()
            continue

        m = _re_chr.match(text, i)
        if m:
            add("CHR" if normalize_literals else m.group(0))
            i = m.end()
            continue

        m = _re_num.match(text, i)
        if m:
            add("NUM" if normalize_literals else m.group(0))
            i = m.end()
            continue

        m = _re_id.match(text, i)
        if m:
            word = m.group(0)
            if word in kws:
                add(word)  # keep keyword
            else:
                add("ID" if normalize_ids else word)
            i = m.end()
            continue

        matched = False
        for op in OPS:
            if text.startswith(op, i):
                add(op)
                i += len(op)
                matched = True
                break
        if matched:
            continue

        add(ch)
        i += 1

    return tokens