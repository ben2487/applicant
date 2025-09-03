import json
import re
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin, urlparse
from ddgs import DDGS
from openai import OpenAI
from webbot.tracing import action, event, json_blob, text, image


async def agentic5_find_apply_url(
    job_url: str,
    job_description_summary: str,
    do_not_apply_domains: List[str],
    page,
    max_rounds: int = 6,
) -> tuple[Optional[str], Dict[str, Any]]:
    """Three-stage deterministic approach to find apply URL."""
    trace = {"stages": {}}
    
    # Stage 1: Find official company website
    print("\n🔍 STAGE 1: Finding official company website...")
    event("FIND_APPLY", "INFO", "agentic5_stage1_start", job_url=job_url)
    
    stage1_result = _stage1_find_official_website(job_url, job_description_summary, page, trace)
    if not stage1_result:
        print("❌ Stage 1 failed: Could not find official company website")
        return None, trace
    
    official_domain = stage1_result["official_domain"]
    print(f"✅ Stage 1 complete: Found official website: {official_domain}")
    
    # Stage 2: Find careers page on official website
    print("\n🔍 STAGE 2: Finding careers page on official website...")
    event("FIND_APPLY", "INFO", "agentic5_stage2_start", official_domain=official_domain)
    
    stage2_result = await _stage2_find_careers_page(official_domain, page, trace)
    if not stage2_result:
        print("❌ Stage 2 failed: Could not find careers page")
        return None, trace
    
    careers_url = stage2_result.get("careers_url")
    apply_url = stage2_result.get("apply_url")
    email_instructions = stage2_result.get("email_instructions")
    
    if apply_url:
        print(f"✅ Stage 2 complete: Found apply URL: {apply_url}")
        return apply_url, trace
    elif careers_url:
        print(f"✅ Stage 2 complete: Found careers page: {careers_url}")
        
        # Stage 3: Validate careers page with optional navigation
        print("\n🔍 STAGE 3: Validating careers page and navigating to specific job...")
        event("FIND_APPLY", "INFO", "agentic5_stage3_start", careers_url=careers_url)
        
        stage3_result = await _stage3_validate_and_navigate(careers_url, job_description_summary, page, trace)
        if stage3_result:
            return stage3_result, trace
        else:
            return careers_url, trace  # Return careers URL as fallback
    elif email_instructions:
        print(f"✅ Stage 2 complete: Found email application instructions: {email_instructions}")
        return None, trace  # Email applications not supported yet
    else:
        print("❌ Stage 2 failed: No careers page, apply URL, or email instructions found")
        return None, trace


def _stage1_find_official_website(job_url: str, job_description_summary: str, page, trace) -> Optional[Dict[str, Any]]:
    """Stage 1: Find the official company website using search."""
    client = OpenAI()
    
    # Extract company name from job description
    company_extract_prompt = f"""
    Extract the company name from this job posting summary. Return only the company name, nothing else.
    
    Job posting: {job_description_summary}
    """
    
    with action("company_extract", category="LLM"):
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": company_extract_prompt}],
            temperature=0.0,
        )
        company_name = resp.choices[0].message.content.strip()
        json_blob("LLM", "DEBUG", "stage1_company_extract", {"prompt": company_extract_prompt, "response": company_name})
    
    print(f"🏢 Company name extracted: {company_name}")
    
    # Search for official website
    search_prompt = f"""
    Find the official company website for "{company_name}". 
    
    Return ONLY a valid JSON object with these exact keys:
    - "official_domain": The official company domain (e.g., "example.com")
    - "confidence": High/Medium/Low
    - "rationale": Brief explanation of why this is the official site
    
    Avoid aggregator sites, job boards, or social media profiles. Focus on the company's main website.
    
    Example response format:
    {{
        "official_domain": "example.com",
        "confidence": "High",
        "rationale": "This is the main company website"
    }}
    """
    
    with action("official_website_search", category="LLM"):
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": search_prompt}],
            temperature=0.0,
        )
        content = resp.choices[0].message.content
        json_blob("LLM", "DEBUG", "stage1_search_response", {"prompt": search_prompt, "response": content})
        
        print(f"🔍 LLM response: {content}")
        
        try:
            result = json.loads(content)
            trace["stages"]["stage1"] = result
            return result
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse Stage 1 JSON response: {e}")
            print(f"❌ Raw response: {repr(content)}")
            return None


async def _stage2_find_careers_page(official_domain: str, page, trace) -> Optional[Dict[str, Any]]:
    """Stage 2: Find careers page on official website."""
    client = OpenAI()
    
    # Load the main page
    main_url = f"https://{official_domain}"
    print(f"🌐 Loading main page: {main_url}")
    
    try:
        await page.goto(main_url, wait_until="domcontentloaded", timeout=15000)
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass  # Continue even if networkidle times out
        
        # Comprehensive scrolling to trigger lazy content
        print("📜 Scrolling to load all content...")
        await page.evaluate("window.scrollTo(0, 0)")  # Start at top
        await page.wait_for_timeout(500)
        
        # Scroll down in chunks
        for i in range(5):
            await page.evaluate(f"window.scrollTo(0, {(i+1) * 1000})")
            await page.wait_for_timeout(300)
        
        # Scroll to bottom
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(1000)
        
        # Scroll back to top
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(500)
        
        # Extract all links
        links = await page.evaluate("""
            () => {
                const anchors = document.querySelectorAll('a[href]');
                return Array.from(anchors).map(a => ({
                    text: a.textContent.trim(),
                    href: a.href,
                    title: a.title || ''
                })).filter(link => link.text.length > 0);
            }
        """)
        
        # Resolve relative URLs to absolute
        resolved_links = []
        for link in links:
            try:
                absolute_url = urljoin(main_url, link["href"])
                resolved_links.append({
                    "text": link["text"],
                    "url": absolute_url,
                    "title": link["title"]
                })
            except Exception:
                continue
        
        print(f"🔗 Found {len(resolved_links)} links on main page")
        json_blob("LINKS", "DEBUG", "stage2_main_page_links", {"count": len(resolved_links), "links": resolved_links[:20]})
        
        # Also check about/company pages for additional links
        all_links = resolved_links.copy()
        about_links = [link for link in resolved_links if any(keyword in link["text"].lower() for keyword in ["about", "company", "team"])]
        
        if about_links:
            print(f"🔍 Found {len(about_links)} about/company links, checking for careers info...")
            for about_link in about_links[:2]:  # Check first 2 about links
                try:
                    print(f"🔍 Visiting about page: {about_link['url']}")
                    await page.goto(about_link["url"], wait_until="domcontentloaded", timeout=10000)
                    try:
                        await page.wait_for_load_state("networkidle", timeout=5000)
                    except Exception:
                        pass
                    
                    # Scroll to load content
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(500)
                    
                    about_page_links = await page.evaluate("""
                        () => {
                            const anchors = document.querySelectorAll('a[href]');
                            return Array.from(anchors).map(a => ({
                                text: a.textContent.trim(),
                                href: a.href,
                                title: a.title || ''
                            })).filter(link => link.text.length > 0);
                        }
                    """)
                    
                    # Resolve relative URLs
                    for link in about_page_links:
                        try:
                            absolute_url = urljoin(about_link["url"], link["href"])
                            all_links.append({
                                "text": link["text"],
                                "url": absolute_url,
                                "title": link["title"]
                            })
                        except Exception:
                            continue
                    
                    print(f"🔗 Added {len(about_page_links)} links from about page")
                    
                except Exception as e:
                    print(f"❌ Error checking about page {about_link['url']}: {e}")
                    continue
        
        print(f"🔗 Total links collected: {len(all_links)}")
        
        # Analyze links with LLM
        links_text = "\n".join([f"- {link['text']}: {link['url']}" for link in all_links[:80]])
        
        link_analysis_prompt = f"""
        Analyze these links from the company's main page and about pages. Look for:
        1. Careers/jobs page links (including footer links, navigation, etc.)
        2. About page links (already visited)
        3. Email application instructions
        4. Any links that might lead to job postings
        
        Total links found: {len(all_links)}
        Links:
        {links_text}
        
        Return ONLY a valid JSON object with these exact keys:
        - "careers_links": List of URLs that appear to be careers/jobs pages (prioritize by relevance)
        - "about_links": List of URLs that appear to be about pages (already checked)
        - "email_instructions": Any text mentioning email applications
        - "analysis": Brief explanation of what you found and which links look most promising
        
        Example response format:
        {{
            "careers_links": ["https://example.com/careers"],
            "about_links": ["https://example.com/about"],
            "email_instructions": "",
            "analysis": "Found careers link in footer"
        }}
        """
        
        with action("link_analysis", category="LLM"):
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": link_analysis_prompt}],
                temperature=0.0,
            )
            content = resp.choices[0].message.content
            json_blob("LLM", "DEBUG", "stage2_link_analysis", {"prompt": link_analysis_prompt, "response": content})
            
            print(f"🔍 Stage 2 LLM response: {content}")
            
            try:
                # Clean up markdown code blocks if present
                cleaned_content = content.strip()
                if cleaned_content.startswith("```json"):
                    cleaned_content = cleaned_content[7:]  # Remove ```json
                if cleaned_content.endswith("```"):
                    cleaned_content = cleaned_content[:-3]  # Remove ```
                cleaned_content = cleaned_content.strip()
                
                analysis = json.loads(cleaned_content)
                print(f"📊 Link analysis: {analysis.get('analysis', 'No analysis provided')}")
                
                # Check careers links first
                careers_links = analysis.get("careers_links", [])
                if careers_links:
                    print(f"🎯 Found {len(careers_links)} potential careers links")
                    for i, url in enumerate(careers_links, 1):
                        print(f"   {i}. {url}")
                    
                    # Visit first careers link
                    careers_url = careers_links[0]
                    print(f"🔍 Visiting careers page: {careers_url}")
                    
                    careers_result = await _analyze_careers_page(careers_url, page, trace)
                    if careers_result:
                        return careers_result
                
                # Check about page if no careers found
                about_links = analysis.get("about_links", [])
                if about_links and not careers_links:
                    print(f"📄 Found {len(about_links)} about page links, checking for careers info")
                    about_url = about_links[0]
                    print(f"🔍 Visiting about page: {about_url}")
                    
                    about_result = await _analyze_about_page(about_url, page, trace)
                    if about_result:
                        return about_result
                
                # Check for email instructions
                email_instructions = analysis.get("email_instructions")
                if email_instructions:
                    print(f"📧 Found email application instructions: {email_instructions}")
                    return {"email_instructions": email_instructions}
                
                print("❌ No careers page, about page, or email instructions found")
                return None
                
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse Stage 2 link analysis JSON: {e}")
                print(f"❌ Raw response: {repr(content)}")
                return None
                
    except Exception as e:
        print(f"❌ Error loading main page: {e}")
        return None


async def _analyze_careers_page(careers_url: str, page, trace) -> Optional[Dict[str, Any]]:
    """Analyze a careers page to find specific job listings."""
    client = OpenAI()
    
    try:
        await page.goto(careers_url, wait_until="domcontentloaded", timeout=15000)
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass  # Continue even if networkidle times out
        
        # Scroll to trigger lazy content
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(1000)
        
        # Extract page content
        page_text = await page.evaluate("document.body.innerText")
        page_title = await page.evaluate("document.title")
        
        print(f"📄 Careers page title: {page_title}")
        print(f"📄 Careers page text length: {len(page_text)} characters")
        
        # Extract job listing links
        job_links = await page.evaluate("""
            () => {
                const anchors = document.querySelectorAll('a[href]');
                return Array.from(anchors).map(a => ({
                    text: a.textContent.trim(),
                    href: a.href,
                    title: a.title || ''
                })).filter(link => link.text.length > 0);
            }
        """)
        
        resolved_job_links = []
        for link in job_links:
            try:
                absolute_url = urljoin(careers_url, link["href"])
                resolved_job_links.append({
                    "text": link["text"],
                    "url": absolute_url,
                    "title": link["title"]
                })
            except Exception:
                continue
        
        print(f"🔗 Found {len(resolved_job_links)} links on careers page")
        
        # Analyze with LLM
        links_text = "\n".join([f"- {link['text']}: {link['url']}" for link in resolved_job_links[:30]])
        
        careers_analysis_prompt = f"""
        Analyze this careers page to find specific job application URLs.
        
        Page title: {page_title}
        Page text preview: {page_text[:1000]}...
        
        Links found:
        {links_text}
        
        Return ONLY a valid JSON object with these exact keys:
        - "apply_url": The best matching job application URL
        - "confidence": High/Medium/Low
        - "rationale": Why this URL was chosen
        - "alternative_urls": List of other potential job URLs
        
        Example response format:
        {{
            "apply_url": "https://example.com/job/123",
            "confidence": "High",
            "rationale": "This URL matches the job title",
            "alternative_urls": ["https://example.com/job/456"]
        }}
        """
        
        with action("careers_analysis", category="LLM"):
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": careers_analysis_prompt}],
                temperature=0.0,
            )
            content = resp.choices[0].message.content
            json_blob("LLM", "DEBUG", "stage2_careers_analysis", {"prompt": careers_analysis_prompt, "response": content})
            
            print(f"🔍 Careers analysis response: {content}")
            
            try:
                # Clean up markdown code blocks if present
                cleaned_content = content.strip()
                if cleaned_content.startswith("```json"):
                    cleaned_content = cleaned_content[7:]  # Remove ```json
                if cleaned_content.endswith("```"):
                    cleaned_content = cleaned_content[:-3]  # Remove ```
                cleaned_content = cleaned_content.strip()
                
                result = json.loads(cleaned_content)
                apply_url = result.get("apply_url")
                confidence = result.get("confidence", "Low")
                rationale = result.get("rationale", "")
                
                print(f"🎯 Careers analysis confidence: {confidence}")
                print(f"🎯 Rationale: {rationale}")
                
                if apply_url:
                    print(f"✅ Found apply URL: {apply_url}")
                    return {"apply_url": apply_url, "careers_url": careers_url}
                else:
                    print("❌ No specific apply URL found on careers page")
                    return {"careers_url": careers_url}
                    
            except json.JSONDecodeError:
                print("❌ Failed to parse careers analysis JSON")
                return {"careers_url": careers_url}
                
    except Exception as e:
        print(f"❌ Error analyzing careers page: {e}")
        return None


async def _analyze_about_page(about_url: str, page, trace) -> Optional[Dict[str, Any]]:
    """Analyze an about page to find careers information."""
    client = OpenAI()
    
    try:
        await page.goto(about_url, wait_until="domcontentloaded", timeout=15000)
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass  # Continue even if networkidle times out
        
        # Extract page content
        page_text = await page.evaluate("document.body.innerText")
        page_title = await page.evaluate("document.title")
        
        print(f"📄 About page title: {page_title}")
        
        # Extract links
        links = await page.evaluate("""
            () => {
                const anchors = document.querySelectorAll('a[href]');
                return Array.from(anchors).map(a => ({
                    text: a.textContent.trim(),
                    href: a.href,
                    title: a.title || ''
                })).filter(link => link.text.length > 0);
            }
        """)
        
        resolved_links = []
        for link in links:
            try:
                absolute_url = urljoin(about_url, link["href"])
                resolved_links.append({
                    "text": link["text"],
                    "url": absolute_url,
                    "title": link["title"]
                })
            except Exception:
                continue
        
        # Look for careers links
        careers_links = [link for link in resolved_links if any(keyword in link["text"].lower() for keyword in ["career", "job", "work", "apply"])]
        
        if careers_links:
            print(f"🎯 Found {len(careers_links)} careers-related links on about page")
            careers_url = careers_links[0]["url"]
            print(f"🔍 Following careers link: {careers_url}")
            
            return await _analyze_careers_page(careers_url, page, trace)
        else:
            print("❌ No careers links found on about page")
            return None
            
    except Exception as e:
        print(f"❌ Error analyzing about page: {e}")
        return None


async def _stage3_validate_and_navigate(careers_url: str, job_description_summary: str, page, trace) -> Optional[str]:
    """Stage 3: Validate careers page and navigate to specific job posting."""
    client = OpenAI()
    
    try:
        print(f"🌐 Loading careers page: {careers_url}")
        await page.goto(careers_url, wait_until="domcontentloaded", timeout=15000)
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass  # Continue even if networkidle times out
        
        # Comprehensive scrolling to load all content
        print("📜 Scrolling careers page to load all content...")
        await page.evaluate("window.scrollTo(0, 0)")  # Start at top
        await page.wait_for_timeout(500)
        
        # Scroll down in chunks
        for i in range(8):  # More scrolling for careers pages
            await page.evaluate(f"window.scrollTo(0, {(i+1) * 800})")
            await page.wait_for_timeout(300)
        
        # Scroll to bottom
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(1000)
        
        # Scroll back to top
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(500)
        
        # Extract page content
        page_text = await page.evaluate("document.body.innerText")
        page_title = await page.evaluate("document.title")
        
        print(f"📄 Careers page title: {page_title}")
        print(f"📄 Careers page text length: {len(page_text)} characters")
        
        # Extract all links
        links = await page.evaluate("""
            () => {
                const anchors = document.querySelectorAll('a[href]');
                return Array.from(anchors).map(a => ({
                    text: a.textContent.trim(),
                    href: a.href,
                    title: a.title || ''
                })).filter(link => link.text.length > 0);
            }
        """)
        
        resolved_links = []
        for link in links:
            try:
                absolute_url = urljoin(careers_url, link["href"])
                resolved_links.append({
                    "text": link["text"],
                    "url": absolute_url,
                    "title": link["title"]
                })
            except Exception:
                continue
        
        print(f"🔗 Found {len(resolved_links)} links on careers page")
        
        # Stage 3 Analysis: Determine page type and navigate accordingly
        stage3_analysis_prompt = f"""
        Analyze this careers page to determine its type and next steps.
        
        Original job search: {job_description_summary}
        Page title: {page_title}
        Page text preview: {page_text[:1500]}...
        
        Links found ({len(resolved_links)} total):
        {chr(10).join([f"- {link['text']}: {link['url']}" for link in resolved_links[:50]])}
        
        Determine if this page is:
        1. A specific job posting page (with detailed job description and apply button)
        2. An ATS job listings page (showing multiple job titles/positions)
        3. An overview/info page (no job postings, just company info)
        
        Return ONLY a valid JSON object with these exact keys:
        - "page_type": "job_posting" | "job_listings" | "overview_page"
        - "confidence": High/Medium/Low
        - "apply_button_found": true/false (if page_type is "job_posting")
        - "apply_button_text": "text of apply button if found"
        - "matching_job_links": ["list of URLs that might match our job search"]
        - "rationale": "explanation of your analysis"
        
        Example response format:
        {{
            "page_type": "job_listings",
            "confidence": "High",
            "apply_button_found": false,
            "apply_button_text": "",
            "matching_job_links": ["https://example.com/job/software-engineer"],
            "rationale": "Found multiple job titles, this is an ATS listings page"
        }}
        """
        
        with action("stage3_analysis", category="LLM"):
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": stage3_analysis_prompt}],
                temperature=0.0,
            )
            content = resp.choices[0].message.content
            json_blob("LLM", "DEBUG", "stage3_analysis", {"prompt": stage3_analysis_prompt, "response": content})
            
            print(f"🔍 Stage 3 analysis response: {content}")
            
            try:
                # Clean up markdown code blocks if present
                cleaned_content = content.strip()
                if cleaned_content.startswith("```json"):
                    cleaned_content = cleaned_content[7:]  # Remove ```json
                if cleaned_content.endswith("```"):
                    cleaned_content = cleaned_content[:-3]  # Remove ```
                cleaned_content = cleaned_content.strip()
                
                analysis = json.loads(cleaned_content)
                page_type = analysis.get("page_type", "unknown")
                confidence = analysis.get("confidence", "Low")
                rationale = analysis.get("rationale", "")
                
                print(f"📊 Page type: {page_type} (confidence: {confidence})")
                print(f"📊 Rationale: {rationale}")
                
                if page_type == "job_posting":
                    # Case 1: We're on a specific job posting page
                    apply_button_found = analysis.get("apply_button_found", False)
                    apply_button_text = analysis.get("apply_button_text", "")
                    
                    if apply_button_found:
                        print(f"🎯 Found apply button: '{apply_button_text}'")
                        print("🖱️ Clicking apply button to navigate to application form...")
                        
                        # Try to click the apply button
                        try:
                            # Look for the apply button by text
                            apply_button = await page.locator(f"text={apply_button_text}").first
                            await apply_button.click()
                            await page.wait_for_timeout(2000)
                            
                            # Check if we now have a form
                            current_url = page.url
                            print(f"✅ Navigated to: {current_url}")
                            
                            # Take screenshot of new page
                            try:
                                png = await page.screenshot(full_page=False)
                                image("BROWSER", "DEBUG", "stage3_after_apply_click", png)
                            except Exception:
                                pass
                            
                            return current_url
                            
                        except Exception as e:
                            print(f"❌ Failed to click apply button: {e}")
                            return None
                    else:
                        print("❌ No apply button found on job posting page")
                        return None
                
                elif page_type == "job_listings":
                    # Case 2: We're on an ATS job listings page
                    matching_job_links = analysis.get("matching_job_links", [])
                    
                    if matching_job_links:
                        print(f"🎯 Found {len(matching_job_links)} potential matching job links")
                        for i, url in enumerate(matching_job_links, 1):
                            print(f"   {i}. {url}")
                        
                        # Visit the first matching job link
                        job_url = matching_job_links[0]
                        print(f"🔍 Visiting potential job posting: {job_url}")
                        
                        # Navigate to the job posting
                        await page.goto(job_url, wait_until="domcontentloaded", timeout=15000)
                        try:
                            await page.wait_for_load_state("networkidle", timeout=10000)
                        except Exception:
                            pass
                        
                        # Scroll to load content
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await page.wait_for_timeout(1000)
                        
                        # Verify this is the right job posting
                        job_page_text = await page.evaluate("document.body.innerText")
                        job_page_title = await page.evaluate("document.title")
                        
                        print(f"📄 Job page title: {job_page_title}")
                        
                        # Use LLM to verify this matches our original search
                        verification_prompt = f"""
                        Verify if this job posting matches our original search.
                        
                        Original search: {job_description_summary}
                        Current page title: {job_page_title}
                        Current page text: {job_page_text[:1000]}...
                        
                        Return ONLY a valid JSON object with:
                        - "matches": true/false
                        - "confidence": High/Medium/Low
                        - "rationale": "explanation of match or mismatch"
                        - "apply_button_found": true/false
                        - "apply_button_text": "text of apply button if found"
                        
                        Example response format:
                        {{
                            "matches": true,
                            "confidence": "High",
                            "rationale": "Job title and requirements match",
                            "apply_button_found": true,
                            "apply_button_text": "Apply for this Job"
                        }}
                        """
                        
                        with action("job_verification", category="LLM"):
                            resp = client.chat.completions.create(
                                model="gpt-4o-mini",
                                messages=[{"role": "user", "content": verification_prompt}],
                                temperature=0.0,
                            )
                            verification_content = resp.choices[0].message.content
                            json_blob("LLM", "DEBUG", "job_verification", {"prompt": verification_prompt, "response": verification_content})
                            
                            print(f"🔍 Job verification response: {verification_content}")
                            
                            try:
                                # Clean up markdown code blocks if present
                                cleaned_content = verification_content.strip()
                                if cleaned_content.startswith("```json"):
                                    cleaned_content = cleaned_content[7:]  # Remove ```json
                                if cleaned_content.endswith("```"):
                                    cleaned_content = cleaned_content[:-3]  # Remove ```
                                cleaned_content = cleaned_content.strip()
                                
                                verification = json.loads(cleaned_content)
                                matches = verification.get("matches", False)
                                confidence = verification.get("confidence", "Low")
                                rationale = verification.get("rationale", "")
                                apply_button_found = verification.get("apply_button_found", False)
                                apply_button_text = verification.get("apply_button_text", "")
                                
                                print(f"📊 Job match: {matches} (confidence: {confidence})")
                                print(f"📊 Rationale: {rationale}")
                                
                                if matches and apply_button_found:
                                    print(f"🎯 Found matching job with apply button: '{apply_button_text}'")
                                    print("🖱️ Clicking apply button...")
                                    
                                    # Try to click the apply button
                                    try:
                                        apply_button = await page.locator(f"text={apply_button_text}").first
                                        await apply_button.click()
                                        await page.wait_for_timeout(2000)
                                        
                                        final_url = page.url
                                        print(f"✅ Navigated to application form: {final_url}")
                                        
                                        # Take screenshot
                                        try:
                                            png = await page.screenshot(full_page=False)
                                            image("BROWSER", "DEBUG", "stage3_final_application_form", png)
                                        except Exception:
                                            pass
                                        
                                        return final_url
                                        
                                    except Exception as e:
                                        print(f"❌ Failed to click apply button: {e}")
                                        return job_url  # Return job URL as fallback
                                elif matches:
                                    print("✅ Found matching job posting")
                                    return job_url
                                else:
                                    print("❌ Job posting doesn't match our search")
                                    return None
                                    
                            except json.JSONDecodeError as e:
                                print(f"❌ Failed to parse job verification JSON: {e}")
                                return job_url  # Return job URL as fallback
                    else:
                        print("❌ No matching job links found in listings")
                        return None
                
                elif page_type == "overview_page":
                    # Case 3: We're on an overview page, look for navigation to job listings
                    print("📄 This appears to be an overview page, looking for job listings navigation...")
                    
                    # Look for common job listing navigation links
                    job_nav_links = [link for link in resolved_links if any(keyword in link["text"].lower() for keyword in ["job", "career", "position", "opening", "apply"])]
                    
                    if job_nav_links:
                        print(f"🎯 Found {len(job_nav_links)} job navigation links")
                        nav_url = job_nav_links[0]["url"]
                        print(f"🔍 Following job navigation link: {nav_url}")
                        
                        # Recursively call Stage 3 on the job listings page
                        return await _stage3_validate_and_navigate(nav_url, job_description_summary, page, trace)
                    else:
                        print("❌ No job navigation links found on overview page")
                        return None
                
                else:
                    print(f"❌ Unknown page type: {page_type}")
                    return None
                    
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse Stage 3 analysis JSON: {e}")
                print(f"❌ Raw response: {repr(content)}")
                return None
                
    except Exception as e:
        print(f"❌ Error in Stage 3: {e}")
        return None
