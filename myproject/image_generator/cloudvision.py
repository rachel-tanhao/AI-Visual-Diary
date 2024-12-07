#https://console.cloud.google.com/iam-admin/serviceaccounts/details/118058091341323201172/permissions?orgonly=true&project=ninth-bonito-438016-m5&supportedpurview=organizationId
import os
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# from https://cloud.google.com/vision/docs/handwriting?hl=zh-cn
def detect_document(path):
    """从图片中提取文字"""
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
            
            # print(f"\nBlock confidence: {block.confidence}\n") # for debugging

            for paragraph in block.paragraphs:
                
                # print("Paragraph confidence: {}".format(paragraph.confidence)) # for debugging

                for word in paragraph.words:
                    word_text = "".join([symbol.text for symbol in word.symbols])
                    paragraph_text.append(word_text)

                    # # print out single letter & word for debugging
                    # print("Word text: {} (confidence: {})".format(word_text, word.confidence))
                    # for symbol in word.symbols:
                    #     print("\tSymbol: {} (confidence: {})".format(symbol.text, symbol.confidence))

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


def parse_diary(image_path):
    """主函数，调用上述两个函数处理日记图片"""
    words = detect_document(image_path)
    extracted_text = format_paragraph(words)
    return extracted_text



# for debugging
# test_doc_path = "./diary_chinese.png.jpg"
# text = detect_document(test_doc_path)
# formatted_paragraph = format_paragraph(text)
# print(formatted_paragraph)
