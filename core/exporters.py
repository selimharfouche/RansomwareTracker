import datetime
import logging
import hashlib
import re
from typing import Dict, List, Any

from config.settings import MISP_SETTINGS

logger = logging.getLogger(__name__)

class MISPExporter:
    """Exports data in MISP format"""
    
    def __init__(self, settings=MISP_SETTINGS):
        self.settings = settings
    
    def generate_feed(self, victims: List[Dict]) -> Dict:
        """Generate MISP feed format"""
        events = []
        
        for victim in victims:
            if not victim.get('domain'):
                continue
            
            group = victim.get('group', 'ransomware')
            
            event = {
                "info": f"{group.capitalize()} Ransomware Victim: {victim.get('domain')}",
                "threat_level_id": self.settings["threat_level"],
                "analysis": self.settings["analysis"],
                "distribution": self.settings["distribution"],
                "date": victim.get('first_seen', datetime.datetime.now().strftime("%Y-%m-%d")),
                "Attribute": []
            }
            
            # Add domain as attribute
            event["Attribute"].append({
                "type": "domain",
                "category": "Network activity",
                "to_ids": False,
                "value": victim.get('domain')
            })
            
            # Add description
            if victim.get('description_preview'):
                event["Attribute"].append({
                    "type": "text",
                    "category": "Other",
                    "to_ids": False,
                    "value": victim.get('description_preview')
                })
                
            # Add full description if available
            if victim.get('description_full'):
                event["Attribute"].append({
                    "type": "text",
                    "category": "Other",
                    "to_ids": False,
                    "value": victim.get('description_full')[:1000] + "..." if len(victim.get('description_full', '')) > 1000 else victim.get('description_full')
                })
                
            # Add deadline if available
            if victim.get('deadline'):
                event["Attribute"].append({
                    "type": "text",
                    "category": "Other",
                    "to_ids": False,
                    "value": f"Deadline: {victim.get('deadline')}"
                })
                
            # Add any contact info
            if victim.get('contact_info'):
                for field, value in victim.get('contact_info', {}).items():
                    if field == 'email':
                        event["Attribute"].append({
                            "type": "email",
                            "category": "Payload delivery",
                            "to_ids": False,
                            "value": value
                        })
                    else:
                        event["Attribute"].append({
                            "type": "text",
                            "category": "Other",
                            "to_ids": False,
                            "value": f"{field.capitalize()}: {value}"
                        })
            
            # Add file links if available
            if victim.get('file_links'):
                for link in victim.get('file_links', []):
                    event["Attribute"].append({
                        "type": "url",
                        "category": "Network activity",
                        "to_ids": False,
                        "value": link
                    })
            
            # Extract any additional IOCs from description
            if victim.get('description_full'):
                # Extract URLs
                urls = re.findall(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[/\w\.-]*', victim.get('description_full', ''))
                for url in urls:
                    if url not in [attr["value"] for attr in event["Attribute"] if attr["type"] == "url"]:
                        event["Attribute"].append({
                            "type": "url",
                            "category": "Network activity",
                            "to_ids": False,
                            "value": url
                        })
                
                # Extract emails
                emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', victim.get('description_full', ''))
                for email in emails:
                    if email not in [attr["value"] for attr in event["Attribute"] if attr["type"] == "email"]:
                        event["Attribute"].append({
                            "type": "email",
                            "category": "Payload delivery",
                            "to_ids": False,
                            "value": email
                        })
            
            # Add tags
            event["Tag"] = list(self.settings["tags"])
            
            # Add group-specific tag
            event["Tag"].append({"name": f"ransomware:{group}"})
            
            events.append(event)
        
        return {"response": events}

class OpenCTIExporter:
    """Exports data in STIX 2.1 format for OpenCTI"""
    
    def generate_feed(self, victims: List[Dict]) -> Dict:
        """Generate OpenCTI STIX 2.1 feed format"""
        stix_objects = []
        
        # Group threat actors by group name
        threat_actors = {}
        
        for victim in victims:
            if not victim.get('domain'):
                continue
                
            group_name = victim.get('group', 'unknown').capitalize()
            
            # Create/get threat actor for this group
            if group_name not in threat_actors:
                actor_id = f"threat-actor--{self._hash_string(group_name)}"
                threat_actors[group_name] = actor_id
                
                # Add threat actor object
                stix_objects.append({
                    "type": "threat-actor",
                    "spec_version": "2.1",
                    "id": actor_id,
                    "created": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "modified": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "name": f"{group_name} Ransomware Group",
                    "description": f"{group_name} ransomware group",
                    "threat_actor_types": ["crime-syndicate", "criminal"]
                })
                
                # Add malware object
                malware_id = f"malware--{self._hash_string(group_name + '-malware')}"
                stix_objects.append({
                    "type": "malware",
                    "spec_version": "2.1",
                    "id": malware_id,
                    "created": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "modified": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "name": f"{group_name} Ransomware",
                    "description": f"Ransomware operated by the {group_name} group",
                    "malware_types": ["ransomware"],
                    "is_family": True
                })
                
                # Add relationship between actor and malware
                stix_objects.append({
                    "type": "relationship",
                    "spec_version": "2.1",
                    "id": f"relationship--{self._hash_string(group_name + '-uses-malware')}",
                    "created": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "modified": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "relationship_type": "uses",
                    "source_ref": actor_id,
                    "target_ref": malware_id
                })
            
            # Create identity for the victim
            victim_id = f"identity--{self._hash_string(victim.get('domain'))}"
            
            # Gather company details for the identity object
            company_name = victim.get('company_name', victim.get('domain'))
            description = victim.get('business_description', victim.get('description_preview', ''))
            
            identity = {
                "type": "identity",
                "spec_version": "2.1",
                "id": victim_id,
                "created": victim.get('first_seen', datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")),
                "modified": victim.get('updated', datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")),
                "name": company_name,
                "description": description,
                "identity_class": "organization",
                "sectors": ["unknown"],  # Could be enhanced with sector detection
                "x_opencti_aliases": [victim.get('domain')]
            }
            
            # Add contact info if available
            contact_info = []
            if victim.get('contact_info'):
                for field, value in victim.get('contact_info', {}).items():
                    contact_info.append(f"{field.capitalize()}: {value}")
            
            if contact_info:
                identity["contact_information"] = "\n".join(contact_info)
                
            stix_objects.append(identity)
            
            # Create relationship between threat actor and victim
            relationship = {
                "type": "relationship",
                "spec_version": "2.1",
                "id": f"relationship--{self._hash_string(group_name + '-targets-' + victim.get('domain'))}",
                "created": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "modified": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "relationship_type": "targets",
                "source_ref": threat_actors[group_name],
                "target_ref": victim_id
            }
            stix_objects.append(relationship)
            
            # Add indicator for domain
            domain_indicator_id = f"indicator--{self._hash_string('domain-' + victim.get('domain'))}"
            stix_objects.append({
                "type": "indicator",
                "spec_version": "2.1",
                "id": domain_indicator_id,
                "created": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "modified": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "name": f"Domain: {victim.get('domain')}",
                "description": f"Domain associated with {group_name} ransomware victim",
                "indicator_types": ["malicious-activity"],
                "pattern": f"[domain-name:value = '{victim.get('domain')}']",
                "pattern_type": "stix",
                "valid_from": victim.get('first_seen', datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"))
            })
            
            # Add relationship between indicator and identity
            stix_objects.append({
                "type": "relationship",
                "spec_version": "2.1",
                "id": f"relationship--{self._hash_string('indicates-' + victim.get('domain'))}",
                "created": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "modified": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "relationship_type": "indicates",
                "source_ref": domain_indicator_id,
                "target_ref": victim_id
            })
            
            # Extract and add file links if available
            if victim.get('file_links'):
                for i, link in enumerate(victim.get('file_links', [])):
                    # Create URL indicator
                    url_indicator_id = f"indicator--{self._hash_string('url-' + link)}"
                    stix_objects.append({
                        "type": "indicator",
                        "spec_version": "2.1",
                        "id": url_indicator_id,
                        "created": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "modified": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "name": f"URL: {link[:50]}...",
                        "description": f"File download link associated with {group_name} ransomware victim",
                        "indicator_types": ["malicious-activity"],
                        "pattern": f"[url:value = '{link}']",
                        "pattern_type": "stix",
                        "valid_from": victim.get('first_seen', datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"))
                    })
                    
                    # Add relationship between URL indicator and identity
                    stix_objects.append({
                        "type": "relationship",
                        "spec_version": "2.1",
                        "id": f"relationship--{self._hash_string('url-indicates-' + victim.get('domain') + str(i))}",
                        "created": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "modified": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "relationship_type": "indicates",
                        "source_ref": url_indicator_id,
                        "target_ref": victim_id
                    })
        
        return {"objects": stix_objects}
    
    def _hash_string(self, input_string: str) -> str:
        """Generate a consistent UUID-like string from input"""
        hash_object = hashlib.md5(input_string.encode())
        hex_dig = hash_object.hexdigest()
        return f"{hex_dig[:8]}-{hex_dig[8:12]}-{hex_dig[12:16]}-{hex_dig[16:20]}-{hex_dig[20:32]}"