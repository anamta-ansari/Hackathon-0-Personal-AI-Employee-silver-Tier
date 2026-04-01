#!/usr/bin/env python3
"""
LinkedIn Content Generator - AI-Powered Post Creation
Generates unique, engaging LinkedIn posts with variety and randomization

Usage:
    python src/skills/linkedin_content_generator.py

Interactive mode:
    - Shows post type options (1-8)
    - Generates UNIQUE content each time
    - Shows preview
    - Saves to Pending_Approval/
    - Ready for approval
"""

import os
import sys
import random
from pathlib import Path
from datetime import datetime, timedelta
import json
import re

# Handle Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')


class LinkedInContentGenerator:
    """
    AI-Powered LinkedIn Content Generator with Randomization
    
    Generates UNIQUE professional LinkedIn posts every time using:
    - Randomized intros (5+ variations per type)
    - Dynamic point elaborations
    - Varied emoji selection
    - Random hashtag pools
    - Different conclusions
    - Context-aware generation
    """

    def __init__(self):
        """Initialize content generator with vault paths and variety pools"""
        # Resolve paths
        self.project_root = Path(__file__).parent.parent.parent
        self.vault_path = self.project_root.parent / 'AI_Employee_Vault'
        self.pending_approval = self.vault_path / 'Pending_Approval'
        self.business_goals = self.vault_path / 'Business_Goals.md'
        self.company_handbook = self.vault_path / 'Company_Handbook.md'
        self.done_folder = self.vault_path / 'Done'
        self.logs_folder = self.vault_path / 'Logs'

        # Ensure pending approval folder exists
        self.pending_approval.mkdir(parents=True, exist_ok=True)

        # ═══════════════════════════════════════════════════════════════
        # VARIETY POOLS - Randomization for unique content every time
        # ═══════════════════════════════════════════════════════════════
        
        # Random intros for each post type
        self.intros = {
            'thought_leadership': [
                "💡 After {timeframe} of {context}, here's what I've learned:",
                "🧠 {number} insights from {context}:",
                "💭 Reflecting on {context}, these lessons stand out:",
                "🎯 What {timeframe} of {context} taught me:",
                "✨ The {number} biggest lessons from {context}:",
                "🔥 Hot take: {context} changed everything",
                "📚 If I could go back, I'd tell myself this:",
            ],
            'milestone': [
                "🎉 Excited to share: {achievement}!",
                "🏆 Big news: We just {achievement}!",
                "🚀 Milestone alert: {achievement}!",
                "⭐ Thrilled to announce {achievement}!",
                "🎊 Celebrating a major win: {achievement}!",
                "💪 Hard work pays off: {achievement}!",
                "🌟 Dream become reality: {achievement}!",
            ],
            'product_update': [
                "📢 New feature alert: {feature}",
                "🆕 Just launched: {feature}",
                "⚡ Introducing {feature}",
                "🎨 We built something cool: {feature}",
                "🔥 Product update: {feature} is live!",
                "✨ Game-changer: {feature}",
                "🚀 Ship day! {feature}",
            ],
            'weekly_summary': [
                "📊 Week {week_number} in review:",
                "🗓️ What happened this week:",
                "📝 Weekly highlights:",
                "🎯 This week's progress:",
                "⚡ Week {week_number} wrap-up:",
                "🔥 This week was WILD:",
                "💪 Crushed it this week:",
            ],
            'team_highlight': [
                "👥 Team spotlight: {team_achievement}",
                "🌟 Meet the minds behind {project}",
                "🎉 Shoutout to the team for {team_achievement}",
                "💪 Incredible work from the crew: {team_achievement}",
                "🚀 Behind every great product: {team_achievement}",
            ],
            'celebration': [
                "🎊 Time to celebrate: {celebration_reason}!",
                "🥳 Cheers to {celebration_reason}!",
                "🎉 Popping champagne: {celebration_reason}!",
                "⭐ Special day: {celebration_reason}!",
                "🌟 Grateful for: {celebration_reason}!",
            ],
            'industry_insight': [
                "🔮 The future of {industry_topic}:",
                "📈 Trending in {industry_topic}:",
                "💡 Unpopular opinion about {industry_topic}:",
                "🧠 Deep dive: {industry_topic}",
                "⚡ Hot take: {industry_topic}",
            ],
        }
        
        # Random transitions
        self.transitions = [
            "Here's what stood out:",
            "Key takeaways:",
            "The highlights:",
            "What matters most:",
            "The essentials:",
            "Breaking it down:",
            "Let me explain:",
            "Here's the thing:",
        ]
        
        # Random conclusions
        self.conclusions = [
            "The {theme} isn't {wrong_way}.\nIt's {right_way}.",
            "What's next? {next_step}.",
            "Looking ahead: {future_vision}.",
            "The journey continues: {next_action}.",
            "{final_thought}\n\nWhat do you think?",
            "Onwards! {motivation}",
            "This is just the beginning. {motivation}",
            "Your turn: {call_to_action}",
        ]
        
        # Emoji pools for variety
        self.emojis = {
            'success': ['🎉', '🚀', '⭐', '🏆', '✨', '🎊', '🔥', '💪', '🌟', '👏'],
            'thinking': ['💡', '🧠', '💭', '🤔', '💬', '🎯', '🔮', '📚', '🧐', '💭'],
            'growth': ['📈', '📊', '⚡', '🌱', '📉', '💹', '🔼', '🔺', '📶', '💯'],
            'numbers': ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟'],
            'tech': ['💻', '🤖', '⚙️', '🔧', '🛠️', '📱', '🖥️', '⌨️', '🖱️', '💾'],
            'business': ['💼', '📋', '📁', '🗂️', '📌', '📎', '✒️', '🖊️', '📝', '📄'],
            'people': ['👥', '👤', '👨‍💼', '👩‍💼', '🧑‍💻', '👨‍🔧', '👩‍🔧', '🤝', '🙌', '👋'],
        }
        
        # Hashtag pools for randomization
        self.hashtag_pools = {
            'ai': ['#AI', '#ArtificialIntelligence', '#MachineLearning', '#DeepLearning', '#MLOps', '#AIAutomation', '#GenerativeAI', '#NeuralNetworks'],
            'startup': ['#Startup', '#Entrepreneur', '#BuildInPublic', '#StartupLife', '#Founder', '#Innovation', '#VentureCapital', '#ScaleUp'],
            'tech': ['#TechLeadership', '#SoftwareEngineering', '#DevLife', '#TechTrends', '#Engineering', '#CloudComputing', '#DevOps', '#SaaS'],
            'productivity': ['#Productivity', '#Automation', '#WorkSmart', '#Efficiency', '#TimeManagement', '#LifeHacks', '#WorkflowOptimization'],
            'leadership': ['#Leadership', '#Management', '#TeamWork', '#CompanyCulture', '#ThoughtLeadership', '#ExecutivePresence', '#StrategicThinking'],
            'future': ['#FutureOfWork', '#DigitalTransformation', '#Industry40', '#TechTrends2026', '#Innovation', '#Disruption', '#NextGen'],
            'general': ['#LinkedIn', '#Professional', '#CareerGrowth', '#Learning', '#Success', '#Motivation', '#Business', '#Networking'],
            'celebration': ['#Milestone', '#Achievement', '#Winning', '#Grateful', '#TeamWork', '#Success', '#Celebration', '#Proud'],
        }
        
        # Post type definitions
        self.post_types = {
            '1': {
                'name': '🏆 Milestone/Achievement',
                'desc': 'Celebrate wins, goals reached, company milestones',
                'generator': self.generate_milestone_post
            },
            '2': {
                'name': '💡 Thought Leadership',
                'desc': 'Share tips, insights, advice on AI/automation',
                'generator': self.generate_thought_leadership_post
            },
            '3': {
                'name': '📢 Product Update',
                'desc': 'Announce new features, releases, improvements',
                'generator': self.generate_product_update_post
            },
            '4': {
                'name': '👥 Team Highlight',
                'desc': 'Behind the scenes, culture, team stories',
                'generator': self.generate_team_highlight_post
            },
            '5': {
                'name': '📊 Weekly Summary',
                'desc': 'Stats, progress, tasks completed this week',
                'generator': self.generate_weekly_summary_post
            },
            '6': {
                'name': '🎉 Celebration',
                'desc': 'Anniversaries, user milestones, achievements',
                'generator': self.generate_celebration_post
            },
            '7': {
                'name': '📚 Industry Insight',
                'desc': 'AI trends, automation tips, predictions',
                'generator': self.generate_industry_insight_post
            },
            '8': {
                'name': '🔥 Custom',
                'desc': 'Describe what you want to post about',
                'generator': self.generate_custom_post
            },
        }

    # ═══════════════════════════════════════════════════════════════
    # HELPER FUNCTIONS FOR RANDOMIZATION
    # ═══════════════════════════════════════════════════════════════

    def _random_intro(self, post_type, **kwargs):
        """Get randomized intro with filled variables"""
        templates = self.intros.get(post_type, ["Here's my latest update:"])
        template = random.choice(templates)
        
        # Fill in variables with random choices
        variables = {
            'timeframe': random.choice(['6 months', '3 months', 'a year', '90 days', 'the past quarter', '8 weeks']),
            'context': random.choice(['building our product', 'leading our team', 'growing our startup', 'this journey', 'working on automation', 'scaling our system']),
            'number': random.choice(['3', '5', '4', 'Three', 'Five', 'Seven']),
            'achievement': kwargs.get('achievement', 'a major milestone'),
            'feature': kwargs.get('feature', 'our new feature'),
            'week_number': datetime.now().isocalendar()[1],
            'team_achievement': random.choice(['shipping v2.0', 'hitting our goals', 'the amazing launch', 'all the hard work']),
            'celebration_reason': random.choice(['this milestone', 'our success', 'the journey so far', 'what we built together']),
            'industry_topic': random.choice(['AI automation', 'the future of work', 'productivity tools', 'tech innovation']),
        }
        
        try:
            return template.format(**variables)
        except KeyError:
            return template

    def _random_hashtags(self, categories, count=None):
        """Generate random hashtags from categories"""
        if count is None:
            count = random.randint(4, 6)
        
        all_tags = []
        
        for category in categories:
            if category in self.hashtag_pools:
                all_tags.extend(self.hashtag_pools[category])
        
        # Add some general tags
        all_tags.extend(self.hashtag_pools['general'])
        
        # Randomly select unique tags
        selected = random.sample(all_tags, min(count, len(all_tags)))
        
        return ' '.join(selected)

    def _random_emojis(self, category, count=1):
        """Get random emojis from category"""
        emojis = self.emojis.get(category, ['✨'])
        return random.sample(emojis, min(count, len(emojis)))

    def _elaborate_point(self, point):
        """Add random elaboration to a point"""
        elaborations = {
            "Automation works best with human oversight": [
                "Don't eliminate humans—augment them.",
                "The goal isn't replacement, it's enhancement.",
                "Humans + AI > AI alone.",
                "Keep humans in the loop for quality.",
            ],
            "Start small, scale gradually": [
                "We began with 1 post/day, now at 5/day.",
                "Rome wasn't built in a day. Neither is a system.",
                "Small wins compound into big results.",
                "Crawl, walk, run—then fly.",
            ],
            "Monitor everything you build": [
                "What gets measured gets improved.",
                "Data > Intuition for optimization.",
                "You can't fix what you can't see.",
                "Dashboards are your best friend.",
            ],
            "Perfect is the enemy of shipped": [
                "Better done than perfect.",
                "Ship, learn, iterate. Repeat.",
                "V1 is supposed to be embarrassing.",
                "Done beats perfect every time.",
            ],
            "User feedback beats assumptions": [
                "Build what they need, not what you think they need.",
                "Talk to users early and often.",
                "Assumptions are expensive. Validation is cheap.",
                "Your users know better than you.",
            ],
        }
        
        if point in elaborations:
            return random.choice(elaborations[point])
        else:
            return random.choice([
                "This changed everything for us.",
                "A hard-earned lesson.",
                "Took time to learn this one.",
                "Wish I knew this sooner.",
                "Game-changer honestly.",
            ])

    # ═══════════════════════════════════════════════════════════════
    # CONTENT GENERATORS - Each produces unique content every time
    # ═══════════════════════════════════════════════════════════════

    def generate_thought_leadership_post(self):
        """Generate UNIQUE thought leadership post with randomization"""
        
        # Random structure choices
        num_points = random.randint(3, 5)
        number_emojis = self._random_emojis('numbers', num_points)
        
        # Dynamic content - randomly select topics
        topics_pool = [
            "Automation works best with human oversight",
            "Start small, scale gradually",
            "Monitor everything you build",
            "Perfect is the enemy of shipped",
            "User feedback beats assumptions",
            "Iterate faster than you think",
            "Measure what matters, ignore the rest",
            "Build for tomorrow, ship for today",
            "Simplicity scales, complexity breaks",
            "Document everything religiously",
        ]
        
        selected_topics = random.sample(topics_pool, num_points)
        
        # Build content
        intro = self._random_intro('thought_leadership')
        transition = random.choice(self.transitions)
        
        points = []
        for i, topic in enumerate(selected_topics):
            emoji = number_emojis[i]
            elaboration = self._elaborate_point(topic)
            points.append(f"{emoji} {topic}\n   {elaboration}")
        
        # Random conclusion with filled variables
        conclusions_filled = {
            'theme': random.choice(['future', 'key', 'secret', 'truth', 'real lesson']),
            'wrong_way': random.choice(['AI vs Humans', 'speed vs quality', 'big vs small', 'perfect vs done']),
            'right_way': random.choice(['AI + Humans = Superhuman', 'speed AND quality', 'big AND small', 'done AND improved']),
            'next_step': random.choice(['Keep building', 'Ship faster', 'Learn more', 'Stay curious']),
            'future_vision': random.choice(['More automation', 'Better tools', 'Smarter systems', 'Human-AI partnership']),
            'next_action': random.choice(['onward and upward', 'building every day', 'shipping weekly', 'learning constantly']),
            'final_thought': random.choice(['Stay curious', 'Keep learning', 'Build in public', 'Share your journey', 'Question everything']),
            'motivation': random.choice(['🚀', '💪', '⚡', '🔥', '🌟']),
            'call_to_action': random.choice(["What's your take?", 'Agree or disagree?', 'Share your experience!', "Let's discuss!"]),
        }
        
        conclusion_template = random.choice(self.conclusions)
        conclusion = conclusion_template.format(**conclusions_filled)
        
        # Combine
        content = f"{intro}\n\n{transition}\n\n"
        content += "\n\n".join(points)
        content += f"\n\n{conclusion}\n\n"
        content += self._random_hashtags(['ai', 'startup', 'tech', 'leadership'], count=random.randint(4, 6))
        
        return content

    def generate_milestone_post(self):
        """Generate UNIQUE milestone post with randomization"""
        
        achievements_pool = [
            "hit 10,000 users",
            "reached $100K MRR",
            "launched in 5 new markets",
            "closed our Series A",
            "hired our 20th employee",
            "shipped 50 features this quarter",
            "processed 1M+ API calls",
            "achieved 99.9% uptime",
            "expanded to 3 continents",
            "partnered with industry leaders",
        ]
        
        achievement = random.choice(achievements_pool)
        intro = self._random_intro('milestone', achievement=achievement)
        
        gratitude_options = [
            "Huge thanks to our amazing team who made this possible.",
            "Couldn't have done it without our incredible community.",
            "This is just the beginning. Onwards! 🚀",
            "Grateful for everyone who believed in us.",
            "To our supporters: you make this possible. Thank you! 🙏",
            "None of this happens without our dedicated team. Love you all! ❤️",
        ]
        
        gratitude = random.choice(gratitude_options)
        
        future_options = [
            "What's next? Even bigger goals.",
            "Now the real work begins.",
            "Here's to the next milestone!",
            "Excited for what's ahead.",
            "Buckle up—it's going to get even better!",
            "This is just chapter one.",
        ]
        
        future = random.choice(future_options)
        
        success_emoji = self._random_emojis('success', 2)
        
        content = f"{success_emoji[0]} {intro}\n\n{gratitude}\n\n{future} {success_emoji[1]}\n\n"
        content += self._random_hashtags(['startup', 'general', 'celebration'], count=random.randint(4, 5))
        
        return content

    def generate_product_update_post(self):
        """Generate UNIQUE product update post with randomization"""
        
        features_pool = [
            "AI-powered content generation",
            "one-click LinkedIn automation",
            "real-time analytics dashboard",
            "smart scheduling assistant",
            "team collaboration tools",
            "automated approval workflows",
            "multi-platform posting",
            "custom branding options",
        ]
        
        feature = random.choice(features_pool)
        intro = self._random_intro('product_update', feature=feature)
        
        benefits_pool = [
            "⚡ 10x faster than manual posting",
            "🎯 Boost engagement by 300%+",
            "💰 Save 10 hours/week",
            "📊 Track everything in real-time",
            "🤖 AI does the heavy lifting",
            "✨ Professional results every time",
            "🔒 Enterprise-grade security",
            "📱 Works on any device",
        ]
        
        benefits = random.sample(benefits_pool, random.randint(3, 4))
        
        cta_options = [
            "Try it free for 14 days →",
            "Early access available now →",
            "Join the waitlist →",
            "Limited beta spots available →",
            "Book a demo today →",
            "See it in action →",
        ]
        
        cta = random.choice(cta_options)
        
        content = f"{intro}\n\n"
        content += "\n".join(benefits)
        content += f"\n\n{cta}\n\n"
        content += self._random_hashtags(['tech', 'startup', 'productivity', 'ai'], count=random.randint(4, 6))
        
        return content

    def generate_weekly_summary_post(self):
        """Generate UNIQUE weekly summary post with randomization"""
        
        intro = self._random_intro('weekly_summary')
        
        highlights_pool = [
            "🚀 Shipped 3 major features",
            "👥 Onboarded 500+ new users",
            "📈 Revenue up 25% MoM",
            "🎯 Hit our Q1 goals early",
            "💻 Reduced bugs by 40%",
            "⚡ 99.9% uptime maintained",
            "🎨 Launched rebrand",
            "📱 Mobile app beta live",
            "🔧 Automated 80% of workflows",
            "📊 Dashboard shows 3x growth",
        ]
        
        highlights = random.sample(highlights_pool, random.randint(4, 6))
        
        next_week_options = [
            "Next week: Even bigger launches 🔥",
            "Coming soon: Major announcements 👀",
            "Next week's focus: Scale, scale, scale 📈",
            "Buckle up—next week is going to be wild 🚀",
            "More updates coming your way soon ⚡",
        ]
        
        next_week = random.choice(next_week_options)
        
        content = f"{intro}\n\n"
        content += "\n".join(highlights)
        content += f"\n\n{next_week}\n\n"
        content += self._random_hashtags(['startup', 'general', 'productivity'], count=random.randint(4, 5))
        
        return content

    def generate_team_highlight_post(self):
        """Generate UNIQUE team highlight post with randomization"""
        
        intro = self._random_intro('team_highlight')
        
        team_aspects_pool = [
            "Daily standups keep us aligned",
            "Code reviews ensure quality",
            "Pair programming solves tough problems",
            "Retrospectives help us improve",
            "Team lunches build culture",
            "Hackathons spark innovation",
            "Knowledge sharing sessions level everyone up",
        ]
        
        aspects = random.sample(team_aspects_pool, random.randint(3, 4))
        
        appreciation_options = [
            "Grateful to work with such talented humans! 🙏",
            "This team makes the impossible possible. 💪",
            "Couldn't ask for better collaborators. ❤️",
            "Team makes the dream work! 🌟",
        ]
        
        appreciation = random.choice(appreciation_options)
        
        content = f"{intro}\n\n"
        content += "What makes our team special:\n\n"
        content += "\n".join(aspects)
        content += f"\n\n{appreciation}\n\n"
        content += self._random_hashtags(['leadership', 'general', 'celebration'], count=random.randint(4, 5))
        
        return content

    def generate_celebration_post(self):
        """Generate UNIQUE celebration post with randomization"""
        
        intro = self._random_intro('celebration')
        
        celebration_reasons_pool = [
            "another year of innovation",
            "thousands of tasks automated",
            "countless hours unlocked",
            "our amazing community",
            "the journey we've shared",
            "what we've built together",
        ]
        
        celebration_reason = random.choice(celebration_reasons_pool)
        intro = intro.replace('{celebration_reason}', celebration_reason)
        
        reflection_options = [
            "Looking back, I'm filled with gratitude for everyone who believed in this vision.",
            "Every challenge taught us something. Every win motivated us further.",
            "From day one to today—what a ride it's been!",
            "Milestones like this remind us why we started.",
        ]
        
        reflection = random.choice(reflection_options)
        
        future_options = [
            "Here's to many more! 🥂",
            "The best is yet to come. 🚀",
            "Onward to the next chapter! 📖",
            "Celebrating today, building tomorrow. 💪",
        ]
        
        future = random.choice(future_options)
        
        celebration_emojis = self._random_emojis('success', 3)
        
        content = f"{celebration_emojis[0]} {intro}\n\n{reflection}\n\n{future} {celebration_emojis[1]} {celebration_emojis[2]}\n\n"
        content += self._random_hashtags(['celebration', 'general', 'startup'], count=random.randint(4, 5))
        
        return content

    def generate_industry_insight_post(self):
        """Generate UNIQUE industry insight post with randomization"""
        
        intro = self._random_intro('industry_insight')
        
        topics_pool = [
            ("Human-AI Collaboration", "Moving beyond simple task automation to true partnership."),
            ("Personal AI Employees", "Every professional will have AI assistants managing workflows."),
            ("Trust Through Transparency", "Audit logs and approval workflows are non-negotiable."),
            ("The Death of Busywork", "Automation frees humans for strategic thinking."),
            ("Rise of No-Code AI", "Soon everyone will build AI workflows without coding."),
        ]
        
        topic, description = random.choice(topics_pool)
        
        elaboration_options = [
            f"We're seeing this play out in real-time with {topic.lower()}.",
            f"The data is clear: {topic.lower()} is transforming industries.",
            f"Industry leaders are betting big on {topic.lower()}.",
            f"Here's why {topic.lower()} matters more than you think:",
        ]
        
        elaboration = random.choice(elaboration_options)
        
        prediction_options = [
            "Mark my words: this will be mainstream within 2 years.",
            "I predict every company will adopt this by 2027.",
            "The organizations that embrace this will dominate their markets.",
            "This isn't a question of if—it's a question of when.",
        ]
        
        prediction = random.choice(prediction_options)
        
        content = f"{intro}\n\n"
        content += f"**{topic}**\n\n"
        content += f"{description}\n\n"
        content += f"{elaboration}\n\n"
        content += f"{prediction}\n\n"
        content += f"What's your take on {topic.lower()}?\n\n"
        content += self._random_hashtags(['ai', 'future', 'tech', 'leadership'], count=random.randint(4, 6))
        
        return content

    def generate_custom_post(self):
        """Generate UNIQUE custom post from user input"""
        
        print("\nDescribe what you'd like to post about:")
        print("(e.g., 'Our new dashboard feature', 'Tips for email automation')")
        
        topic = input("\nTopic: ").strip()
        
        if not topic:
            print("No topic provided. Generating thought leadership post instead.")
            return self.generate_thought_leadership_post()
        
        # Random intro styles
        intro_styles = [
            f"💭 Insights on {topic}",
            f"🔥 Hot take: {topic}",
            f"📚 Deep dive: {topic}",
            f"💡 Thoughts on {topic}",
            f"🎯 My perspective: {topic}",
        ]
        
        intro = random.choice(intro_styles)
        
        # Random value-add content
        value_adds = [
            "Here's what I've learned after working with this extensively:",
            "After implementing this in production, here are my findings:",
            "The community keeps asking about this—so let me share:",
            "This topic comes up constantly. Here's my two cents:",
        ]
        
        value_add = random.choice(value_adds)
        
        # Random insights
        insights_pool = [
            "Innovation in this area is accelerating faster than expected",
            "Best practices are still emerging—now is the time to experiment",
            "Early adopters are seeing significant competitive advantages",
            "The tools have finally caught up with the vision",
            "What seemed impossible last year is now routine",
        ]
        
        insights = random.sample(insights_pool, random.randint(2, 3))
        
        # Random conclusion
        conclusions_pool = [
            "The future belongs to those who embrace change while maintaining quality.",
            "Stay curious, keep experimenting, and share what you learn!",
            "This is just the beginning. Exciting times ahead!",
            "Your turn: What's your experience with this?",
        ]
        
        conclusion = random.choice(conclusions_pool)
        
        content = f"{intro}\n\n{value_add}\n\n"
        content += "\n".join(f"• {insight}" for insight in insights)
        content += f"\n\n{conclusion}\n\n"
        
        # Generate relevant hashtags from topic
        topic_words = topic.lower().replace(',', '').replace('.', '').split()
        custom_hashtags = [f"#{word[:15]}" for word in topic_words if len(word) > 3][:3]
        
        content += self._random_hashtags(['general'], count=3)
        if custom_hashtags:
            content += " " + " ".join(custom_hashtags)
        
        return content

    # ═══════════════════════════════════════════════════════════════
    # FILE SAVING & INTERACTIVE MODE
    # ═══════════════════════════════════════════════════════════════

    def save_post_to_pending(self, content, post_type):
        """Save generated post to Pending_Approval folder"""
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_type = re.sub(r'[^a-zA-Z0-9]', '_', post_type.lower())[:20]
        filename = f"LINKEDIN_{safe_type}_{timestamp}.md"
        filepath = self.pending_approval / filename

        # Create frontmatter
        frontmatter = f"""---
type: approval_request
action: linkedin_post
post_type: {post_type}
category: social_media
status: awaiting_approval
created: {datetime.now().isoformat()}
generated_by: ai_content_generator_v2
---

# LinkedIn Post Approval Request

## Post Content

{content}

---

## Approval Instructions

Review the post content above.

**✅ To Publish:** Move this file to `/Approved/`
**❌ To Reject:** Move this file to `/Rejected/`
**✏️ To Edit:** Modify content above and then move to `/Approved/`

---
*Generated by AI Employee - LinkedIn Content Generator v2 (Unique Content Every Time)*
"""

        # Save file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(frontmatter)

        return filepath

    def show_post_options(self):
        """Display post type options to user"""
        print("\n" + "=" * 70)
        print("🎨 LINKEDIN CONTENT GENERATOR")
        print("=" * 70)
        print("\n✨ Each generation produces UNIQUE content—run multiple times for variety!\n")
        print("Choose post type:\n")

        for key, value in self.post_types.items():
            print(f"{key}. {value['name']}")
            print(f"   {value['desc']}\n")

        return self.post_types

    def get_user_selection(self):
        """Get user's post type selection"""
        while True:
            choice = input("Your choice (1-8): ").strip()
            if choice in self.post_types:
                return choice
            print("Invalid choice. Please enter 1-8.")

    def run_interactive(self):
        """Run interactive post generation"""
        # Show options
        self.show_post_options()

        # Get user selection
        choice = self.get_user_selection()

        # Generate content based on selection
        post_info = self.post_types[choice]
        print(f"\n✨ Generating {post_info['name']}...\n")

        content = post_info['generator']()

        # Show preview
        print("\n" + "=" * 70)
        print("📝 GENERATED POST PREVIEW")
        print("=" * 70)
        print(content)
        print("=" * 70)

        # Confirm
        confirm = input("\n✅ Save this post to Pending_Approval? (y/n): ").strip().lower()

        if confirm == 'y':
            filepath = self.save_post_to_pending(content, post_info['name'])

            print(f"\n✅ Post saved to: {filepath.name}")
            print(f"\n📝 Next steps:")
            print(f"   1. Review: type \"{filepath}\"")
            print(f"   2. Approve: move {filepath.name} AI_Employee_Vault\\Approved\\")
            print(f"   3. Watch automation publish it to LinkedIn!")
            print(f"\n💡 Tip: Run again to generate a DIFFERENT version of this post type!")
            print()
        else:
            print("\n❌ Post discarded. Run again to generate a new one.")


def main():
    """Main entry point for interactive post generation"""
    print("\n" + "=" * 70)
    print("🤖 AI Employee - LinkedIn Content Generator v2")
    print("=" * 70)
    print("\n🎲 Randomization enabled: Every run produces UNIQUE content!")
    print("=" * 70)

    generator = LinkedInContentGenerator()
    generator.run_interactive()


if __name__ == "__main__":
    main()
