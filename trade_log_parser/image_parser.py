import os
import pandas as pd
import glob
from datetime import datetime
import pytesseract
from PIL import Image
import logging
import cv2

# Ensure the logs directory exists
os.makedirs('logs', exist_ok=True)

# Set up logging configuration with both a file handler and a stream handler
log_filename = datetime.now().strftime('logs/trade_log_%Y%m%d_%H%M%S.log')
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),  # Log to file
        logging.StreamHandler()             # Log to console
    ]
)

class TradingLogProcessor:
    def __init__(self, input_dir, output_file):
        self.input_dir = input_dir
        self.output_file = output_file
        self.all_trades = []
        # Define the headers we're looking for
        self.required_headers = ['Ticker', 'XP', 'Long/Short', 'Average Entry', 'Size', 'Average Exit']

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

    def find_trading_section(self, lines):
        """Find the section that contains trades after 'Closed Trades'"""
        section_start = None
        for i, line in enumerate(lines):
            if "Closed Trades" in line:
                section_start = i
                break

        if section_start is not None:
            # Skip blank lines after "Closed Trades"
            for j in range(section_start + 1, len(lines)):
                if lines[j].strip():  # Find the first non-blank line
                    section_start = j
                    break

            # Look for the end of the section
            for k in range(section_start, len(lines)):
                if 'Blue Deer Trading' in lines[k] or 'Weekly P/L' in lines[k]:
                    return lines[section_start:k]
            
            # If no end found, return to the end
            return lines[section_start:]
        
        return []

    def process_image(self, image_path):
        """Process a single trading log image and extract trade data"""
        try:
            logging.info(f"Processing image: {image_path}")
            # Preprocess the image
            preprocessed_image = self.preprocess_image(image_path)
            
            # Extract text from image using pytesseract
            text = pytesseract.image_to_string(preprocessed_image)
            
            # Log the OCR output
            logging.debug(f"OCR output for {image_path}:\n{text}")
            
            # Split into lines and find relevant section
            lines = text.split('\n')
            trading_section = self.find_trading_section(lines)
            
            if not trading_section:
                logging.warning(f"No trading section found in {image_path}")
                return []
            
            # Parse the trading section
            trades = self.parse_trading_section(trading_section)
            
            # Get the week date from filename or image content
            week_date = self.extract_week_date(image_path)
            
            # Add week date to each trade
            for trade in trades:
                trade['Trade Week'] = week_date
            
            logging.info(f"Extracted {len(trades)} trades from {image_path}")
            return trades
            
        except Exception as e:
            logging.error(f"Error processing image {image_path}: {str(e)}")
            return []

    def parse_trading_section(self, section_lines):
        """Parse the trading section lines into structured data"""
        trades = []
        # Skip the header line
        data_lines = [line.strip() for line in section_lines[1:] if line.strip()]
        
        for line in data_lines:
            try:
                # Split the line into components
                parts = line.split()
                if len(parts) < 6:  # Skip invalid lines
                    continue
                
                # Extract values with better handling of missing data
                ticker = parts[0]
                if ticker == "S":
                    ticker = "ES"
                
                xp = parts[1] if len(parts) > 1 and '/' not in parts[1] else ''
                long_short = next((p for p in parts[1:4] if p in ['long', 'short', 'lotto']), '')
                
                # Find numeric values
                numbers = [p for p in parts if any(c.isdigit() for c in p)]
                
                if len(numbers) < 4:  # Need at least entry, size, exit, and P/L
                    continue
                
                trade = {
                    'Ticker': ticker,
                    'XP': xp,
                    'Long/Short': long_short,
                    'Average Entry': self.parse_number(numbers[0]),
                    'Size': numbers[1] if 'x' in numbers[1] else f"{numbers[1]}x",
                    'Average Exit': self.parse_number(numbers[2]),
                    'Percentage Change': self.parse_percentage(parts),
                    'P/L Per Unit': self.parse_pl_unit(parts),
                    'Realized P/L': self.parse_pl_total(parts)
                }
                trades.append(trade)
                
            except Exception as e:
                logging.error(f"Error parsing line: {line}, Error: {str(e)}")
                continue
                
        return trades

    @staticmethod
    def parse_number(value):
        """Parse a number from string, handling various formats"""
        try:
            return float(value.replace(',', ''))
        except:
            return 0

    @staticmethod
    def parse_percentage(parts):
        """Extract percentage change from parts"""
        for part in parts:
            if '%' in part:
                try:
                    return float(part.replace('%', '').replace('+', ''))
                except:
                    pass
        return 0

    @staticmethod
    def parse_pl_unit(parts):
        """Extract P/L per unit from parts"""
        for i, part in enumerate(parts):
            if '$' in part and i < len(parts) - 1:
                try:
                    return float(part.replace('$', '').replace('+', ''))
                except:
                    pass
        return 0

    @staticmethod
    def parse_pl_total(parts):
        """Extract total P/L from parts"""
        for part in reversed(parts):  # Look from the end
            if '$' in part:
                try:
                    return float(part.replace('$', '').replace('+', '').replace(',', ''))
                except:
                    pass
        return 0

    def extract_week_date(self, image_path):
        """Extract week date from filename or image content"""
        filename = os.path.splitext(os.path.basename(image_path))[0]
        try:
            date = datetime.strptime(filename[:8], '%Y%m%d')
            return date.strftime('%Y-%m-%d')
        except:
            return ''

    def process_all_images(self):
        """Process all images in the input directory"""
        image_files = glob.glob(os.path.join(self.input_dir, '*.jpg')) + \
                     glob.glob(os.path.join(self.input_dir, '*.png'))
        
        logging.info(f"Found {len(image_files)} images to process.")
        for image_file in image_files[:10]:  # Limit to 10 images for testing
            trades = self.process_image(image_file)
            self.all_trades.extend(trades)

    def save_to_csv(self):
        """Save all processed trades to CSV file"""
        if not self.all_trades:
            logging.warning("No trades to save")
            return
            
        df = pd.DataFrame(self.all_trades)
        
        columns = ['Trade Week', 'Ticker', 'XP', 'Long/Short', 'Average Entry', 'Size', 
                  'Average Exit', 'Percentage Change', 'P/L Per Unit', 'Realized P/L']
        df = df[columns]
        
        df.to_csv(self.output_file, index=False)
        logging.info(f"Saved {len(self.all_trades)} trades to {self.output_file}")

def main():
    input_directory = "trading_logs/"
    output_file = "combined_trades.csv"
    
    processor = TradingLogProcessor(input_directory, output_file)
    processor.process_all_images()
    processor.save_to_csv()

if __name__ == "__main__":
    main()