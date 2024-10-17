#https://console.cloud.google.com/iam-admin/serviceaccounts/details/118058091341323201172/permissions?orgonly=true&project=ninth-bonito-438016-m5&supportedpurview=organizationId
import os
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/Users/apple/Desktop/cis581 cv/final project/ninth-bonito-438016-m5-f01175447fef.json"

# from https://cloud.google.com/vision/docs/handwriting?hl=zh-cn
def detect_document(path):
    """Detects document features in an image."""
    from google.cloud import vision

    client = vision.ImageAnnotatorClient()

    with open(path, "rb") as image_file:
        content = image_file.read()

    image = vision.Image(content=content)

    # language code: https://cloud.google.com/vision/docs/languages
    # default is english, image_context={"language_hints": ["zh"] = chinese, "es" = spanish
    response = client.document_text_detection(image=image, image_context={"language_hints": ["zh"]}) 

    # to store whole text
    paragraph_text = []  

    for page in response.full_text_annotation.pages:
        for block in page.blocks:
            print(f"\nBlock confidence: {block.confidence}\n")

            for paragraph in block.paragraphs:
                print("Paragraph confidence: {}".format(paragraph.confidence))

                for word in paragraph.words:
                    word_text = "".join([symbol.text for symbol in word.symbols])
                    paragraph_text.append(word_text)
                    print(
                        "Word text: {} (confidence: {})".format(
                            word_text, word.confidence
                        )
                    )

                    for symbol in word.symbols:
                        print(
                            "\tSymbol: {} (confidence: {})".format(
                                symbol.text, symbol.confidence
                            )
                        )

    if response.error.message:
        raise Exception(
            "{}\nFor more info on error messages, check: "
            "https://cloud.google.com/apis/design/errors".format(response.error.message)
        )
    return paragraph_text

def format_paragraph(words):
    # Join the list of words into a single string with spaces
    paragraph = ''.join(words)
    return paragraph

text = detect_document('diary_chinese.png')
formatted_paragraph = format_paragraph(text)
print(formatted_paragraph)
