#!/usr/bin/env python3
"""
Data cleanup script for Telegram visa conversation CSV files.
Processes and cleans the 909,920+ messages for better vector processing.
"""

import pandas as pd
import re
import argparse
from pathlib import Path
from typing import Optional


class VisaDataCleaner:
    def __init__(self):
        self.stats = {
            'original_count': 0,
            'after_basic_cleanup': 0,
            'after_dedup': 0,
            'after_language_filter': 0,
            'final_count': 0
        }
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if pd.isna(text) or text == '':
            return ''
        
        # Convert to string and strip
        text = str(text).strip()
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove system messages patterns
        system_patterns = [
            r'^Forwarded from:',
            r'^Photo$',
            r'^Video$', 
            r'^Document$',
            r'^Sticker$',
            r'^Voice message$',
            r'^Location shared$'
        ]
        
        for pattern in system_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return ''
        
        # Remove URLs (optional - keep if visa-related)
        # text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        return text.strip()
    
    def is_english_or_relevant(self, text: str) -> bool:
        """Check if text is in English or contains relevant visa terms."""
        if not text:
            return False
        
        # Visa-related terms in various languages
        visa_terms = [
            'visa', 'passport', 'embassy', 'consulate', 'h1b', 'f1', 'l1', 'b1', 'b2',
            'interview', 'appointment', 'ds-160', 'ds160', 'i-797', 'i797', 
            'dropbox', 'biometric', 'stamping', 'approval', 'denial', 'pending',
            'administrative', '221g', 'processing', 'uscis', 'department of state'
        ]
        
        text_lower = text.lower()
        
        # Keep if contains visa terms
        if any(term in text_lower for term in visa_terms):
            return True
        
        # Basic English check (rough heuristic)
        english_chars = sum(1 for c in text if c.isascii() and c.isalpha())
        total_alpha = sum(1 for c in text if c.isalpha())
        
        if total_alpha == 0:
            return len(text.split()) <= 3  # Keep short messages
        
        english_ratio = english_chars / total_alpha
        return english_ratio > 0.7  # 70% English characters
    
    def remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicate messages."""
        print("🔍 Removing duplicates...")
        
        # Remove exact duplicates
        df_dedup = df.drop_duplicates(subset=['content'])
        
        # Remove near-duplicates (same content, different timestamps)
        # Group by content and keep the earliest timestamp
        df_dedup = df_dedup.groupby('content').first().reset_index()
        
        return df_dedup
    
    def clean_csv(self, input_file: str, output_file: Optional[str] = None) -> pd.DataFrame:
        """Main cleaning function."""
        print(f"🚀 Starting cleanup of {input_file}")
        
        # Load data
        df = pd.read_csv(input_file)
        self.stats['original_count'] = len(df)
        print(f"📊 Original messages: {self.stats['original_count']:,}")
        
        # Step 1: Basic cleanup
        print("\n🧹 Step 1: Basic text cleanup...")
        df['content_clean'] = df['content'].apply(self.clean_text)
        
        # Remove messages with no content
        df = df[df['content_clean'].str.len() >= 10]  # At least 10 characters
        self.stats['after_basic_cleanup'] = len(df)
        print(f"✅ After basic cleanup: {self.stats['after_basic_cleanup']:,}")
        
        # Step 2: Remove duplicates
        df = self.remove_duplicates(df)
        self.stats['after_dedup'] = len(df)
        print(f"✅ After deduplication: {self.stats['after_dedup']:,}")
        
        # Step 3: Language filtering
        print("\n🌐 Step 3: Language and relevance filtering...")
        df['is_relevant'] = df['content_clean'].apply(self.is_english_or_relevant)
        df = df[df['is_relevant'] == True]
        self.stats['after_language_filter'] = len(df)
        print(f"✅ After language filtering: {self.stats['after_language_filter']:,}")
        
        # Step 4: Final cleanup
        print("\n✨ Step 4: Final cleanup...")
        
        # Sort by timestamp for chronological processing
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        
        # Keep only necessary columns
        columns_to_keep = [
            'message_id', 'content_clean', 'timestamp', 'user_id', 
            'first_name', 'last_name', 'message_type', 'reply_to_id'
        ]
        df_final = df[columns_to_keep].copy()
        df_final.rename(columns={'content_clean': 'content'}, inplace=True)
        
        self.stats['final_count'] = len(df_final)
        print(f"✅ Final clean dataset: {self.stats['final_count']:,}")
        
        # Save cleaned data
        if output_file:
            df_final.to_csv(output_file, index=False)
            print(f"💾 Saved to: {output_file}")
        
        # Print summary
        self.print_summary()
        
        return df_final
    
    def print_summary(self):
        """Print cleanup summary."""
        print("\n" + "="*50)
        print("📈 CLEANUP SUMMARY")
        print("="*50)
        print(f"Original messages:     {self.stats['original_count']:,}")
        print(f"After basic cleanup:   {self.stats['after_basic_cleanup']:,}")
        print(f"After deduplication:   {self.stats['after_dedup']:,}")
        print(f"After language filter: {self.stats['after_language_filter']:,}")
        print(f"Final clean dataset:   {self.stats['final_count']:,}")
        
        reduction = ((self.stats['original_count'] - self.stats['final_count']) / 
                    self.stats['original_count'] * 100)
        print(f"\nReduction: {reduction:.1f}%")
        print(f"Quality improvement: {100-reduction:.1f}% relevant data retained")


def main():
    parser = argparse.ArgumentParser(description="Clean Telegram visa conversation CSV")
    parser.add_argument("input_file", help="Input CSV file path")
    parser.add_argument("-o", "--output", help="Output CSV file path")
    
    args = parser.parse_args()
    
    # Default output filename
    if not args.output:
        input_path = Path(args.input_file)
        args.output = str(input_path.parent / f"{input_path.stem}_cleaned.csv")
    
    # Run cleanup
    cleaner = VisaDataCleaner()
    cleaner.clean_csv(args.input_file, args.output)
    
    print(f"\n🎉 Cleanup complete! Run vector processing with:")
    print(f'docker compose --profile vectors run --rm vector-processor python simple_vector_processor.py --csv "{args.output}"')


if __name__ == "__main__":
    main()

