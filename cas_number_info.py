import re
import requests
from cat.mad_hatter.decorators import tool, hook

# disable warnings
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

def get_cas_property(html_page, search_str):
    #>Log Kow (Log Pow)</dt><dd>2.9 @ 20 C</dd>
    start = html_page.find(search_str)

    if start > 0:
        finish = html_page.find("<", start + len(search_str))

        if finish > 0:
            return html_page[start + len(search_str): finish]
    
    return ""

# strip unwanted characters to make property search easier (without using specialized libraries)
def html_cleansing(html_page):
    clean_html = html_page.replace("\\n","").replace("\\r","").replace("\\t","").replace("b\'","").replace("\'","").replace("&#xb0;","").replace("&nbsp;"," ")
    clean_html = re.sub(" +", " ", clean_html).replace("> ",">").replace(" <","<")

    return clean_html

@hook
def agent_prompt_prefix(cat):
    prefix = """You are Chem, an expert on chemical compounds.
"""

    return prefix

@tool(return_direct=True)
def cas_properties(cas, cat):
    """Replies to "CAS number". Input is the CAS number of the chemical."""

    wanted_properties = [
        {
            'property_name': 'Log Pow',
            'property_value': '',
            'property_search_string': '>Log Pow</dt><dd>',
            'property_search_string_2': '>Log Kow (Log Pow)</dt><dd>'
        },
        {
            'property_name': 'Flash point',
            'property_value': '',
            'property_search_string': '>Flash point</dt><dd>',
            'property_search_string_2': '>Flash point at 101 325 Pa</dt><dd>'
        },
        {
            'property_name': 'Vapour pressure',
            'property_value': '',
            'property_search_string': '>Vapour pressure</dt><dd>',
            'property_search_string_2': ''
        },
        {
            'property_name': 'Boiling point',
            'property_value': '',
            'property_search_string': '>Boiling point</dt><dd>',
            'property_search_string_2': ''
        },
        {
            'property_name': 'Dynamic viscosity',
            'property_value': '',
            'property_search_string': '>dynamic viscosity (in mPa s)</dt><dd>',
            'property_search_string_2': ''
        }
    ]
    
    # ECHA search form
    url = "https://echa.europa.eu/en/search-for-chemicals?p_p_id=disssimplesearch_WAR_disssearchportlet"

    # Create a dictionary with the form data
    form_data = {
        '_disssimplesearch_WAR_disssearchportlet_searchOccurred': True,
        '_disssimplesearch_WAR_disssearchportlet_sskeywordKey': cas
    }

    # send the request suppressing certificate warning and giving consent to GDPR
    req = requests.post(f"{url}", form_data, verify=False, cookies = {'CONSENT' : 'YES+'})

    html = str(req.content)

    # Search for the chemical name
    cas_name = ""
    search_str = "https://echa.europa.eu/en/substance-information/-/substanceinfo/"

    start = html.find(search_str)
    if start > 0:
        start = html.find(">", start + 1)

        if start > 0:
            finish = html.find("<", start + 1)

            cas_name = html_cleansing(html[start + 1: finish])

    # Is there a brief profile (detail page containing chemical properties)?
    search_str = "https://echa.europa.eu/en/brief-profile/-/briefprofile/"

    start = html.find(search_str)
    
    if start > 0:
        finish = html.find("\"", start)
        if finish > 0:
            doc = html[start + len(search_str): finish]

            detail_page = html[start: finish]

            req = requests.get(f"{detail_page}", verify=False, cookies = {'CONSENT' : 'YES+'})

            html = html_cleansing(str(req.content))

            results = f"<a href='{search_str}{doc}' target='_blank'>{cas}</a>\nName: {cas_name}"

            for cas_property in wanted_properties:
                cas_property['property_value'] = get_cas_property(html, cas_property['property_search_string'])
                if cas_property['property_value'] == "" and cas_property['property_search_string_2'] != "":
                    cas_property['property_value'] = get_cas_property(html, cas_property['property_search_string_2'])

                results += f"\n{cas_property['property_name']}: {cas_property['property_value']}"

        return results

    return "CAS profile not found"