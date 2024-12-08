from googletrans import Translator

def translate_text(description, target_lang='ko'):
    translator = Translator()
    translated = translator.translate(description, dest=target_lang)
    return translated.text

if __name__ == "__main__":
    description = "Bitcoin is a decentralized digital currency, without a central bank or single administrator, that can be sent from user to user on the peer-to-peer bitcoin network without the need for intermediaries."
    translated = translate_text(description)
    print(translated)