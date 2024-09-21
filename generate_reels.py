import os
import datetime
import pathlib
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from pymongo import MongoClient

# Load environment variables and set up OpenAI client
load_dotenv()
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# MongoDB connection settings
MONGO_URI = "mongodb://localhost:27017/"
DATABASE_NAME = "reels-content"
COLLECTION_NAME = "content"

# Connect to MongoDB
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[DATABASE_NAME]
collection = db[COLLECTION_NAME]

topic_history = set()

def LLMResponse(prompt):
    completion = openai_client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[
            {"role": "system", "content": "You are a helpful assistant knowledgeable in AI/ML concepts."},
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    return completion

def generate_content():
    global topic_history
    max_attempts = 5

    for _ in range(max_attempts):
        # get the current topic
        topic_response = LLMResponse(f"Suggest a unique AI/ML topic that can be explained in under 150 words. Please provide only the topic without a description. Avoid these topics: {', '.join(topic_history)}.")
        topic = topic_response.choices[0].message.content.strip().lower()
        
        if topic not in topic_history:
            topic_history.add(topic)
            # get the current content
            content_response = LLMResponse(f"Explain the concept of {topic} in simple terms in less than 150 words for youtube shorts. Try to keep it as engaging and as interesting as possible (Don't include any hashtags).")
            content = content_response.choices[0].message.content
            return topic, content
    
    raise Exception("Unable to generate a unique topic after multiple attempts")

def generate_audio(text, filename):
    
    audio_file_path = pathlib.Path(__file__).parent / "audio_files" / filename

    response = openai_client.audio.speech.create(
        model='tts-1',
        voice='echo',
        input=text
    )

    response.stream_to_file(audio_file_path)
    return audio_file_path

def main():
    try:
        topic, content = generate_content()

        # Generate filename using timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        audio_filename = f"audio_{timestamp}.mp3"
        audio_path = generate_audio(topic+content, audio_filename)

        output_dict = {
            "topic": topic,
            "content": content,
            "audio_file": str(audio_path)
        }

        # Insert dictionary into MongoDB
        result = collection.insert_one(output_dict)


        print(f"Data inserted with ID: {result.inserted_id}")
        print(f"Information spoken in the audio file: {topic + content}")
        print(f"Audio file generated: {audio_path}")

    except Exception as e:
        print(f"Error generating content: {e}")

    finally:
        # Close MongoDB connection
        mongo_client.close()

if __name__ == "__main__":
    main()