import os
import pandas as pd
import glob
import base64
import anthropic
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv
import logging
import abc
import openai
import time
import random

load_dotenv()

class AIClient(abc.ABC):
    @abc.abstractmethod
    def send_prompt_with_image(self, prompt: str, image_base64: str) -> str:
        pass

class AnthropicClientImpl(AIClient):
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)

    def send_prompt_with_image(self, prompt: str, image_base64: str) -> str:
        message = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1500,
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_base64
                            }
                        }
                    ]
                }
            ]
        )
        return message.content[0].text.strip()

class OpenAIClientImpl(AIClient):
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)

    def send_prompt_with_image(self, prompt: str, image_base64: str) -> str:
        data_uri = f"data:image/png;base64,{image_base64}"
        retries = 5
        backoff_factor = 0.5

        for attempt in range(retries):
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",  # Corrected model name from "gpt-4o-mini" to "gpt-4"
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert in finance, understanding the intricacies of stock trading, options trading, etc."
                        },
                        {
                            "role": "user",
                            "content": prompt,
                            "image": data_uri
                        }
                    ],
                    max_tokens=300,
                )
                return response.choices[0].message.content.strip()
            except openai.RateLimitError as e:
                wait = backoff_factor * (2 ** attempt) + random.uniform(0, 0.1)
                logging.warning(f"Rate limit exceeded. Retrying in {wait:.2f} seconds...")
                time.sleep(wait)
            except Exception as e:
                logging.error(f"Unexpected error: {str(e)}")
                break
        raise Exception("Failed to fetch response from OpenAI after multiple retries.")

class TradingLogProcessor:
    def __init__(self, input_dir, output_file, ai_client: AIClient):
        self.input_dir = input_dir
        self.output_file = output_file
        self.all_trades = []
        self.client = ai_client
        
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)  # Set root logger to DEBUG

        # File handler for debug logs
        fh = logging.FileHandler("logs/trade_log_parser.log")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s:%(message)s'))

        # Console handler for info logs
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter('%(asctime)s %(levelname)s:%(message)s'))

        logger.addHandler(fh)
        logger.addHandler(ch)

    def encode_image(self, image_path):
        """Convert image to base64 string"""
        with Image.open(image_path) as img:
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            return base64.b64encode(buffered.getvalue()).decode('utf-8')

    def process_image(self, image_path):
        """Process a single trading log image using the configured AI client"""
        try:
            # Encode image
            base64_image = self.encode_image(image_path)

            # Extract date from image path
            basename = os.path.basename(image_path)
            date = f"{basename.split('_')[0][:4]}-{basename.split('_')[0][4:6]}-{basename.split('_')[0][6:]}"
            
            # Construct the prompt
            prompt = """
            This image contains a trading log. Please extract all trades from the "Closed Trades" section. 
            If there are no closed trades, return an empty list. 
            If there are sections above the "Closed Trades" section, ignore them.
            Return the data in CSV format with these exact columns:
            Ticker,XP,Long/Short,Average Entry,Size,Average Exit,Percentage Change,P/L Per Unit,Realized P/L

            Please always double check the Average Entry and Average Exit to make sure they are correct.

            Important notes:
            1. Only extract from the "Closed Trades" section
            2. Include all numeric values exactly as shown
            3. Return ONLY the CSV data, no other text
            4. Don't add headers to the CSV
            5. For blank numeric fields, use 0
            6. Leave XP and Long/Short blank if not specified
            7. Keep the exact formatting of numbers (don't convert to scientific notation)
            8. Do NOT include the size suffix 'x' in the Size column, just use the number
            """

            # Make API call using the abstract client
            csv_data = self.client.send_prompt_with_image(prompt, base64_image)

            basename = os.path.basename(image_path)
            logging.debug(f"CSV data: {csv_data}")
            return self.parse_csv_response(csv_data, date, basename)

        except Exception as e:
            logging.error(f"Error processing image {image_path}: {str(e)}")
            return []

    def parse_csv_response(self, csv_text, date, image_path):
        """Parse CSV response from Claude into list of trade dictionaries"""
        trades = []
        for line in csv_text.split('\n'):
            if line.strip():
                parts = line.split(',')
                if len(parts) >= 9:  # Ensure we have all columns
                    ticker = ''.join(c for c in parts[0].split(' ')[0][:next((i for i, c in enumerate(parts[0].split(' ')[0]) if c.isdigit()), len(parts[0].split(' ')[0]))])
                    trade = {
                        'Trade Week': date,
                        'Ticker': ticker,
                        'Trade String': parts[0],
                        'XP': parts[1],
                        'Long/Short': parts[2],
                        'Average Entry': self.safe_float(parts[3]),
                        'Size': parts[4],
                        'Average Exit': self.safe_float(parts[5]),
                        'Percentage Change': self.safe_float(parts[6]),
                        'P/L Per Unit': self.safe_float(parts[7]),
                        'Realized P/L': self.safe_float(parts[8]),
                        "Image Path": image_path
                    }
                    trades.append(trade)
        return trades

    @staticmethod
    def safe_float(value):
        """Safely convert string to float, handling empty strings and invalid values"""
        try:
            return float(value.strip()) if value.strip() else 0.0
        except (ValueError, AttributeError):
            return 0.0

    def process_all_images(self):
        """Process all images in the input directory"""
        image_files = glob.glob(os.path.join(self.input_dir, '*.jpg')) + \
                     glob.glob(os.path.join(self.input_dir, '*.png'))
        
        for image_file in image_files:
            logging.info(f"Processing {image_file}...")
            trades = self.process_image(image_file)
            self.all_trades.extend(trades)

    def process_n_images(self, n):
        """Process the first n images in the input directory"""
        image_files = glob.glob(os.path.join(self.input_dir, '*.jpg')) + \
                     glob.glob(os.path.join(self.input_dir, '*.png'))
        for image_file in image_files[:n]:
            logging.info(f"Processing {image_file}...")
            trades = self.process_image(image_file)
            logging.info(f"Trades: {len(trades)}")
            self.all_trades.extend(trades)

    def save_to_csv(self):
        """Save all processed trades to CSV file"""
        if not self.all_trades:
            logging.warning("No trades to save")
            return
            
        df = pd.DataFrame(self.all_trades)
        columns = ['Trade Week', 'Ticker', 'Trade String', 'XP', 'Long/Short', 'Average Entry', 'Size', 
                   'Average Exit', 'Percentage Change', 'P/L Per Unit', 'Realized P/L', 'Image Path']
        df = df[columns]
        df.to_csv(self.output_file, index=False)
        logging.info(f"Saved {len(self.all_trades)} trades to {self.output_file}")

def main():
    input_directory = "trading_logs/"
    output_file = "combined_trades.csv"
    api_provider = os.getenv("AI_PROVIDER", "anthropic").lower()
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    if api_provider == "anthropic":
        client = AnthropicClientImpl(api_key=anthropic_api_key)
    elif api_provider == "openai":
        client = OpenAIClientImpl(api_key=openai_api_key)
    else:
        logging.error(f"Unsupported AI provider: {api_provider}")
        return
    
    processor = TradingLogProcessor(input_directory, output_file, client)
    processor.process_n_images(5)
    processor.save_to_csv()

if __name__ == "__main__":
    main()