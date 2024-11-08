import spacy

nlp = spacy.load("zh_core_web_sm")

def extract_key_information(narration):
    doc = nlp(narration)
    events = []
    for sent in doc.sents:
        subject = None
        action = None
        for token in sent:
            if token.dep_ == "nsubj":
                subject = token.text
            if token.dep_ == "ROOT":
                action = token.text
        if subject and action:
            events.append((subject, action, sent.text))
    return events

# 示例文本
narration = "离别总是伤感的，绪花和好友阿孝告别。阿孝突然告白：“我喜欢你！”绪花表示：你在说啥呢？这突然的告白真是让人措手不及，阿孝，你这一招是学来的吧？"
key_info = extract_key_information(narration)
print(key_info)