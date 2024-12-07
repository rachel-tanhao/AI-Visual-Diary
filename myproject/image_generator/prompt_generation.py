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
            - Each phrase should:  
            1. Include a clear sense of **emotion** or **atmosphere** (e.g., “laughing under a sky full of stars”).  
            2. Highlight **dynamic actions** (e.g., “spinning,” “reaching,” “dancing”).  
            3. Emphasize **interaction** with other people, objects, or the environment if mentioned (e.g., “sharing a slice of cake under fairy lights”).  

            **Format:**  
            - Output a list of phrases, each on its own line.  
            - Do not include numbering or bullet points.  

            **Few-Shot Examples:**

            **Example 1:**
            Input Diary Entry:
            "I woke up early and went for a morning jog. Then I returned home and baked some bread. In the afternoon, I sat under an old oak tree and read a book."

            Desired Output:
            "leaping over puddles during a sunrise jog, the air crisp and cool"  
            "pulling golden bread from a warm oven, steam curling into the air"  
            "reading quietly beneath a sprawling oak tree, sunlight dappling the pages"

            **Example 2:**
            Input Diary Entry:
            "After breakfast, I went cycling along the river. Later, I painted a watercolor landscape on my balcony. In the evening, I listened to jazz in a dimly lit café."

            Desired Output:
            "speeding along a riverbank with wind in my hair, the water glimmering beside me"  
            "sweeping a paintbrush over paper, colors blending under soft sunlight"  
            "swaying gently to jazz music in a cozy, dim-lit café, a steaming coffee nearby"

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