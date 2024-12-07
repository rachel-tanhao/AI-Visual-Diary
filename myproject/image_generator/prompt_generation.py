import os
import google.generativeai as genai
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in environment variables")
genai.configure(api_key=api_key)


def process_diary_text(diary_text):
    """ 使用 Gemini 将日记文本转换为场景描述列表 """
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        prompt = f"""
            You are an expert at converting diary entries into concise, descriptive image prompts.

            **Your Task:**  
            - Break down the given diary entry into a list of short, activity-based phrases.  
            - Each phrase should take the writer of the diary as the subject and depict a distinct action or activity of him/her.  
            - Avoid full sentences, connective words, and unnecessary details.  
            - Focus on creating prompts suitable for image generation.

            **Format:**  
            - Output a list of phrases, each on its own line.
            - Do not include numbering or bullet points.

            **Few-Shot Examples:**

            **Example 1:**
            Input Diary Entry:
            "I woke up early and went for a morning jog. Then I returned home and baked some bread. In the afternoon, I sat under an old oak tree and read a book."

            Desired Output:
            "jogging through early morning light"  
            "kneading fresh dough in a cozy kitchen"  
            "reading quietly beneath a sprawling oak tree"

            **Example 2:**
            Input Diary Entry:
            "After breakfast, I went cycling along the river. Later, I painted a watercolor landscape on my balcony. In the evening, I listened to jazz in a dimly lit café."

            Desired Output:
            "cycling beside a calm riverbank"  
            "brushing gentle colors onto paper"  
            "sipping coffee with soft jazz tunes"

            **Now, please apply the same style and process to the following diary entry:**

            {diary_text}
        """
        
        response = model.generate_content(prompt)
        
        # generate scene list
        scene_list = []
        for sentence in response.text.split('\n'):
            sentence = sentence.strip()
            if sentence:
                scene_list.append(sentence)
        
        logger.info(f"Generated {len(scene_list)} scenes from diary text")
        return scene_list
        
    except Exception as e:
        logger.error(f"Error processing diary text: {str(e)}")
        raise 