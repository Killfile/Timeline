"""
LLM-based Event Categorizer

Modular utility for assigning categories to historical events using OpenAI's API.
Designed to be reusable in both experimentation and production ingestion pipelines.

Responsibilities:
- Format event data for LLM prompts
- Batch submit events to OpenAI API
- Parse and validate category responses
- Handle errors and retries gracefully
"""

import os
import json
from typing import List, Dict, Optional, Tuple
from openai import OpenAI


# Standard categories used in the timeline
STANDARD_CATEGORIES = [
    "Politics",
    "War & Conflict",
    "Science & Technology",
    "Arts & Culture",
    "Religion",
    "Economics & Trade",
    "Natural Disasters",
    "Exploration & Discovery",
    "Social Movements",
    "Crime & Punishment",
    "Sports",
    "Attrocities",
    "Other",
    "Disasters",
    "Arab World",
    "Africa",
    "Architecture",
    "Asia",
    "Asia Minor",
    "Assyria",
    "Byzantine Empire",
    "Carthage",
    "China",
    "Climate and Weather",
    "Economy",
    "Education",
    "Egypt",
    "Europe",
    "Exploration",
    "Greece",
    "India",
    "Middle East",
    "Mongol Empire",
    "North America",
    "Persia",
    "Persian Empire",
    "Religion",
    "Rome",
    "Sardinia",
    "Spain",
]


class LLMCategorizer:
    """
    Categorizes historical events using OpenAI's language models.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """
        Initialize the categorizer.
        
        Args:
            api_key: OpenAI API key (defaults to OPEN_AI_API_KEY env var)
            model: OpenAI model to use (default: gpt-4o-mini for cost-effectiveness)
        """
        self.api_key = api_key or os.environ.get('OPEN_AI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key is required (via parameter or OPEN_AI_API_KEY env var)")
        
        self.model = model
        self.client = OpenAI(api_key=self.api_key)
    
    def format_event_for_prompt(self, event: Dict) -> str:
        """
        Format a single event as a string for inclusion in the prompt.
        
        Args:
            event: Dict with keys: id, title, description, start_year, start_month, start_day,
                   end_year, end_month, end_day, is_bc_start, is_bc_end
        
        Returns:
            Formatted string representation of the event
        """
        # Format dates
        start_date = self._format_date(
            event.get('start_year'),
            event.get('start_month'),
            event.get('start_day'),
            event.get('is_bc_start', False)
        )
        
        end_date = self._format_date(
            event.get('end_year'),
            event.get('end_month'),
            event.get('end_day'),
            event.get('is_bc_end', False)
        )
        
        # Build event string
        parts = [f"Event ID: {event['id']}"]
        parts.append(f"Title: {event['title']}")
        
        if event.get('description'):
            parts.append(f"Description: {event['description']}")
        
        if start_date:
            if end_date and end_date != start_date:
                parts.append(f"Time Period: {start_date} to {end_date}")
            else:
                parts.append(f"Date: {start_date}")
        
        return "\n".join(parts)
    
    def _format_date(self, year: Optional[int], month: Optional[int], 
                     day: Optional[int], is_bc: bool) -> Optional[str]:
        """Format a date with optional month/day and BC/AD handling."""
        if year is None:
            return None
        
        era = "BC" if is_bc else "AD"
        
        if month and day:
            return f"{year}-{month:02d}-{day:02d} {era}"
        elif month:
            return f"{year}-{month:02d} {era}"
        else:
            return f"{year} {era}"
    
    def categorize_events(self, events: List[Dict]) -> List[Dict[str, any]]:
        """
        Categorize a batch of events using the LLM.
        
        Args:
            events: List of event dicts (must include id, title, dates)
        
        Returns:
            List of dicts with keys: event_id, category, confidence, reasoning
            
        Raises:
            Exception: If API call fails or response is invalid
        """
        if not events:
            return []
        
        # Build the prompt
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(events)
        
        # Call OpenAI API
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,  # Lower temperature for more consistent categorization
                response_format={"type": "json_object"}
            )
            
            # Parse response
            result_text = response.choices[0].message.content
            result_json = json.loads(result_text)
            
            # Validate and return
            return self._parse_categorization_response(result_json, events)
            
        except Exception as e:
            raise Exception(f"Failed to categorize events: {str(e)}")
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt defining the categorization task."""
        categories_list = "\n".join(f"- {cat}" for cat in STANDARD_CATEGORIES)
        
        return f"""You are a historical event categorization assistant. Your task is to assign each historical event to ONE of the following categories:

{categories_list}

Guidelines:
- Choose the MOST appropriate single category for each event
- Base your decision on the event's primary historical significance
- Use "War & Conflict" for military actions, battles, wars, and armed conflicts
- Use "Politics" for governmental changes, elections, treaties, and political movements
- Use "Science & Technology" for inventions, discoveries, and technological advances
- Use "Arts & Culture" for artistic works, cultural movements, and entertainment
- Use "Religion" for religious events, theological developments, and church history
- Use "Economics & Trade" for economic policies, trade agreements, and financial events
- Use "Natural Disasters" for earthquakes, floods, famines, and natural catastrophes
- Use "Exploration & Discovery" for expeditions, geographical discoveries, and colonization
- Use "Social Movements" for civil rights, labor movements, and social reforms
- Use "Crime & Punishment" for significant criminal events, legal cases, and law enforcement actions
- Use "Disasters" for man-made disasters like industrial accidents, plane crashes, non-wartime sinkings, etc.
- Use "Sports" for major sporting events, competitions, and athletic achievements
- Use "Atrocities" for significant acts of violence, cruelty, and human rights abuses which are not primarily military conflicts
- Use the name of a specific region (e.g., "Europe", "Middle East") for events primarily significant to that area
- Use "Other" only when no other category fits well

You must respond with valid JSON in this exact format:
{{
  "categorizations": [
    {{
      "event_id": <id>,
      "category": "<category name>",
      "confidence": <0.0-1.0>,
      "reasoning": "<brief explanation>"
    }},
    ...
  ]
}}"""
    
    def _build_user_prompt(self, events: List[Dict]) -> str:
        """Build the user prompt with event data."""
        event_strings = []
        for i, event in enumerate(events, 1):
            event_strings.append(f"\n--- Event {i} ---\n{self.format_event_for_prompt(event)}")
        
        return "Please categorize the following events:\n" + "\n".join(event_strings)
    
    def _parse_categorization_response(self, response: Dict, 
                                       original_events: List[Dict]) -> List[Dict]:
        """
        Parse and validate the LLM's categorization response.
        
        Args:
            response: Parsed JSON response from LLM
            original_events: Original events for validation
        
        Returns:
            List of validated categorization results
        """
        if 'categorizations' not in response:
            raise ValueError("Response missing 'categorizations' field")
        
        categorizations = response['categorizations']
        
        # Validate we got results for all events
        event_ids = {e['id'] for e in original_events}
        result_ids = {c['event_id'] for c in categorizations}
        
        if event_ids != result_ids:
            missing = event_ids - result_ids
            extra = result_ids - event_ids
            raise ValueError(
                f"Categorization mismatch. Missing IDs: {missing}, Extra IDs: {extra}"
            )
        
        # Validate each categorization
        results = []
        for cat in categorizations:
            # Validate required fields
            if 'event_id' not in cat or 'category' not in cat:
                raise ValueError(f"Invalid categorization: {cat}")
            
            # Validate category is in standard list
            if cat['category'] not in STANDARD_CATEGORIES:
                # Try to find close match
                cat['category'] = self._find_closest_category(cat['category'])
            
            # Ensure confidence is present and valid
            confidence = cat.get('confidence', 0.8)
            if not 0 <= confidence <= 1:
                confidence = 0.8
            
            results.append({
                'event_id': cat['event_id'],
                'category': cat['category'],
                'confidence': confidence,
                'reasoning': cat.get('reasoning', '')
            })
        
        return results
    
    def _find_closest_category(self, category: str) -> str:
        """Find closest matching standard category (simple fuzzy match)."""
        category_lower = category.lower()
        
        # Simple mappings for common variations
        mappings = {
            'military': 'War & Conflict',
            'warfare': 'War & Conflict',
            'battle': 'War & Conflict',
            'government': 'Politics',
            'political': 'Politics',
            'science': 'Science & Technology',
            'technology': 'Science & Technology',
            'invention': 'Science & Technology',
            'art': 'Arts & Culture',
            'culture': 'Arts & Culture',
            'music': 'Arts & Culture',
            'literature': 'Arts & Culture',
            'religious': 'Religion',
            'church': 'Religion',
            'economy': 'Economics & Trade',
            'economic': 'Economics & Trade',
            'trade': 'Economics & Trade',
            'disaster': 'Natural Disasters',
            'earthquake': 'Natural Disasters',
            'flood': 'Natural Disasters',
            'exploration': 'Exploration & Discovery',
            'discovery': 'Exploration & Discovery',
            'social': 'Social Movements',
            'movement': 'Social Movements'
        }
        
        for key, value in mappings.items():
            if key in category_lower:
                return value
        
        # Default to Other if no match
        return 'Other'


def categorize_events_batch(events: List[Dict], model: str = "gpt-4o-mini",
                            api_key: Optional[str] = None) -> List[Dict]:
    """
    Convenience function to categorize a batch of events.
    
    Args:
        events: List of event dicts
        model: OpenAI model to use
        api_key: OpenAI API key (optional, uses env var if not provided)
    
    Returns:
        List of categorization results
    """
    categorizer = LLMCategorizer(api_key=api_key, model=model)
    return categorizer.categorize_events(events)
