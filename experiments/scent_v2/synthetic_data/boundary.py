"""Identity-only extraction and value-skipping parser for protected histories.

Unlike json.load, forbidden users' item/rating fields are never decoded into data
objects. Original text is read only for structural skipping/hash, not modeling.
"""
import json


class Cursor:
    def __init__(self,text):self.text=text;self.pos=0;self.numeric_decodes=0
    def ws(self):
        while self.pos<len(self.text)and self.text[self.pos].isspace():self.pos+=1
    def take(self,char):
        self.ws()
        if self.text[self.pos]!=char:raise ValueError('Unexpected JSON structure')
        self.pos+=1
    def string(self):
        self.ws();value,end=json.JSONDecoder().raw_decode(self.text,self.pos)
        if not isinstance(value,str):raise ValueError('Expected ID/key string')
        self.pos=end;return value
    def skip(self):
        self.ws();s=self.text;i=self.pos
        if s[i]in '[{':
            stack=[s[i]];i+=1;quoted=False;escape=False
            while stack:
                c=s[i];i+=1
                if quoted:
                    if escape:escape=False
                    elif c=='\\':escape=True
                    elif c=='"':quoted=False
                elif c=='"':quoted=True
                elif c in '[{':stack.append(c)
                elif c in ']}':
                    opening=stack.pop()
                    if (opening,c)not in (('[',']'),('{','}')):raise ValueError('Mismatched JSON')
            self.pos=i
        elif s[i]=='"':
            i+=1;escape=False
            while i<len(s):
                c=s[i];i+=1
                if escape:escape=False
                elif c=='\\':escape=True
                elif c=='"':break
            self.pos=i
        else:
            while i<len(s)and s[i]not in ',]} \t\r\n':i+=1
            self.pos=i
    def number(self):
        self.ws();value,end=json.JSONDecoder().raw_decode(self.text,self.pos);self.numeric_decodes+=1;self.pos=end
        if isinstance(value,bool)or not isinstance(value,(int,float)):raise ValueError('Expected rating number')
        return float(value)


def evaluation_users(text):
    """Read only fold users arrays; train/support/answers are structurally skipped."""
    c=Cursor(text);c.take('[');users=set();folds=0
    while True:
        c.ws()
        if c.text[c.pos]==']':c.pos+=1;break
        c.take('{');found=False
        while True:
            c.ws()
            if c.text[c.pos]=='}':c.pos+=1;break
            key=c.string();c.take(':')
            if key=='users':
                c.take('[')
                while True:
                    c.ws()
                    if c.text[c.pos]==']':c.pos+=1;break
                    u=c.string()
                    if u in users:raise ValueError('Evaluation cohort overlap')
                    users.add(u);c.ws()
                    if c.text[c.pos]==',':c.pos+=1
                found=True
            else:c.skip()
            c.ws()
            if c.text[c.pos]==',':c.pos+=1
        if not found:raise ValueError('Missing evaluation identity cohort')
        folds+=1;c.ws()
        if c.text[c.pos]==',':c.pos+=1
    if c.numeric_decodes:raise AssertionError('No manifest numeric fields may be decoded')
    return users,dict(folds=folds,evaluation_users=len(users),manifest_numeric_decodes=0)


def safe_train(text,excluded):
    """Decode numbers only after checking user ID; skip excluded item AND rating."""
    c=Cursor(text);c.take('[');rows=[];allusers=set();total=0;skipped=0
    while True:
        c.ws()
        if c.text[c.pos]==']':c.pos+=1;break
        c.take('[');u=c.string();allusers.add(u);c.take(',');total+=1
        if u in excluded:c.skip();c.take(',');c.skip();skipped+=1
        else:
            item=c.string();c.take(',');rating=c.number();rows.append((u,item,rating))
        c.take(']');c.ws()
        if c.text[c.pos]==',':c.pos+=1
    assert c.numeric_decodes==len(rows)
    return rows,allusers,dict(source_rows=total,source_user_IDs=len(allusers),excluded_user_rows_skipped_before_rating_decode=skipped,eligible_rows=len(rows),eligible_users=len({u for u,i,y in rows}),numeric_ratings_decoded=len(rows),excluded_user_rating_values_decoded=0,excluded_user_item_IDs_decoded=0)
