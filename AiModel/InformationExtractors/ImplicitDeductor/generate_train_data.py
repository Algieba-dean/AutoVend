import json
import random
import nltk
from nltk.corpus import wordnet
import os

# Download WordNet if not already available
try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')
    nltk.download('punkt')

def get_synonyms(word):
    """Get synonyms for a word using WordNet."""
    synonyms = set()
    
    # Skip short words, stopwords, and special characters
    if len(word) <= 3 or not word.isalpha():
        return []
    
    # Get all synsets for the word
    for syn in wordnet.synsets(word):
        for lemma in syn.lemmas():
            synonym = lemma.name().replace('_', ' ')
            if synonym != word and synonym not in synonyms:
                synonyms.add(synonym)
    
    return list(synonyms)

def replace_with_synonym(text, probability=0.3):
    """Replace words in text with synonyms based on probability."""
    words = nltk.word_tokenize(text)
    result = []
    
    for word in words:
        # Only attempt replacement with certain probability
        if random.random() < probability and word.isalpha():
            synonyms = get_synonyms(word.lower())
            if synonyms:
                # Choose a random synonym
                replacement = random.choice(synonyms)
                # Preserve original capitalization
                if word[0].isupper():
                    replacement = replacement.capitalize()
                result.append(replacement)
            else:
                result.append(word)
        else:
            result.append(word)
    
    return ' '.join(result)

def generate_sample(value, expressions, attribute_name, default_labels):
    """Generate a sample with replaced synonyms for an expression."""
    expression = random.choice(expressions)
    expression_with_synonyms = replace_with_synonym(expression)
    
    # Create a copy of default labels and update the specific attribute
    labels = default_labels.copy()
    labels[attribute_name] = value
    
    return {
        "query": expression_with_synonyms,
        "labels": labels
    }

def create_default_labels(all_attributes):
    """Create default labels with 'none' values for all attributes."""
    default_labels = {}
    for attribute in all_attributes:
        # For boolean attributes (those with only 'yes' value), set default to 'no'
        if attribute in ['abs', 'voice_interaction', 'remote_parking', 'auto_parking', 
                         'city_commuting', 'highway_long_distance', 'cargo_capability']:
            default_labels[attribute] = "no"
        else:
            default_labels[attribute] = "none"
    return default_labels

def main():
    # Load implicit expressions
    with open('ImplicitExpression.json', 'r', encoding='utf-8') as f:
        implicit_data = json.load(f)
    
    # Create default labels
    all_attributes = implicit_data.keys()
    default_labels = create_default_labels(all_attributes)
    
    # Generate samples
    samples = []
    
    for attribute_name, attribute_values in implicit_data.items():
        for value_obj in attribute_values:
            value = value_obj["value"]
            expressions = value_obj["expressions"]
            
            # Generate multiple samples for each value to increase diversity
            num_samples = 3  # Generate 3 samples per expression type
            for _ in range(num_samples):
                sample = generate_sample(value, expressions, attribute_name, default_labels)
                samples.append(sample)
    
    # Shuffle samples for randomness
    random.shuffle(samples)
    
    # Prepare output data
    output_data = {"samples": samples}
    
    # Save to train_data.json
    with open('train_data.json', 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=4, ensure_ascii=False)
    
    print(f"Generated {len(samples)} training samples in train_data.json")

if __name__ == "__main__":
    main() 