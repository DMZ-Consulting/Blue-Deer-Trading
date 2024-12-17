import os
import pandas as pd
import glob
import cv2
import numpy as np
import pytesseract
from PIL import Image

class TradingLogProcessor:
    def __init__(self, input_dir, output_file):
        self.input_dir = input_dir
        self.output_file = output_file
        self.all_trades = []

    def preprocess_image(self, image_path):
        """Preprocess the image to improve OCR accuracy"""
        # Read image with OpenCV
        img = cv2.imread(image_path)
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply thresholding to get rid of the background
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        
        # Apply dilation to connect text
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
        dilated = cv2.dilate(thresh, kernel, iterations=1)
        
        # Convert back to PIL Image for pytesseract
        return Image.fromarray(dilated)

    def clean_text(self, text):
        """Clean up common OCR errors"""
        replacements = {
            'spvaao': 'SPY440',
            'assc': '455C',
            'aze': '43C',
            '4505.50': '4505.50',  # Preserve exact prices
            '.378¢': '378C',
            '175¢': '175C',
            'lw': 'IWM',
            '|': '',  # Remove vertical bars
            '..': '.',  # Fix double dots
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
            
        return text

    def parse_line(self, line):
        """Parse a single line of trade data with improved number handling"""
        try:
            parts = line.split()
            if len(parts) < 4:  # Need at least ticker, date, price, and size
                return None
                
            # Clean up common OCR errors in numbers
            parts = [p.replace('O', '0').replace('o', '0').replace('l', '1') for p in parts]
            
            trade = {
                'Ticker': parts[0].upper(),  # Convert ticker to uppercase
                'XP': '',
                'Long/Short': '',
                'Average Entry': 0.0,
                'Size': '0x',
                'Average Exit': 0.0,
                'Percentage Change': 0.0,
                'P/L Per Unit': 0.0,
                'Realized P/L': 0.0
            }
            
            # Look for date in standard format
            for part in parts:
                if '/' in part:
                    trade['XP'] = part
                    break
                    
            # Look for trading type
            for part in parts:
                if part.lower() in ['core', 'long', 'short', 'lotto']:
                    trade['Long/Short'] = part.lower()
                    break
                    
            # Find numeric values
            numbers = []
            for part in parts:
                try:
                    num = float(part.replace('x', '').replace('$', '').replace(',', ''))
                    numbers.append(num)
                except ValueError:
                    continue
                    
            if len(numbers) >= 2:
                trade['Average Entry'] = numbers[0]
                # Look for size (usually has 'x' suffix)
                for part in parts:
                    if 'x' in part.lower():
                        trade['Size'] = part
                        break
                        
                if len(numbers) >= 3:
                    trade['Average Exit'] = numbers[-1]
                    
            return trade
            
        except Exception as e:
            print(f"Error parsing line: {line}, Error: {str(e)}")
            return None

    def process_image(self, image_path):
        """Process a single trading log image with improved preprocessing"""
        try:
            # Preprocess image
            processed_img = self.preprocess_image(image_path)
            
            # Extract text with improved OCR settings
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz./$ x()"'
            text = pytesseract.image_to_string(processed_img, config=custom_config)
            
            # Clean up the text
            text = self.clean_text(text)
            
            # Split into lines and find relevant section
            lines = text.split('\n')
            trades = []
            
            for line in lines:
                if line.strip() and not line.startswith('Blue Deer') and 'Weekly P/L' not in line:
                    trade = self.parse_line(line)
                    if trade:
                        trades.append(trade)
            
            return trades
            
        except Exception as e:
            print(f"Error processing image {image_path}: {str(e)}")
            return []

    def process_all_images(self):
        """Process all images in the input directory"""
        image_files = glob.glob(os.path.join(self.input_dir, '*.jpg')) + \
                     glob.glob(os.path.join(self.input_dir, '*.png'))
        
        for image_file in image_files:
            trades = self.process_image(image_file)
            self.all_trades.extend(trades)

    def save_to_csv(self):
        """Save all processed trades to CSV file"""
        if not self.all_trades:
            print("No trades to save")
            return
            
        df = pd.DataFrame(self.all_trades)
        columns = ['Trade Week', 'Ticker', 'XP', 'Long/Short', 'Average Entry', 'Size', 
                  'Average Exit', 'Percentage Change', 'P/L Per Unit', 'Realized P/L']
        df = df[columns]
        df.to_csv(self.output_file, index=False)
        print(f"Saved {len(self.all_trades)} trades to {self.output_file}")