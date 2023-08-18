from cat.mad_hatter.decorators import tool, hook
import re
import requests

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

@hook
def agent_prompt_prefix(cat):

    prefix = """You are Chem, an expert on chemical compounds.
"""

    return prefix

@tool(return_direct=True)
def cas_properties(cas, cat):
    """Replies to "CAS number". Input is the CAS number of the chemical."""

    properties = [
        {
            'property_name': 'Log Pow',
            'property_value': '',
            'property_search_string': '>Log Pow</dt><dd>',
            'property_search_string_2': '>Log Kow (Log Pow)</dt><dd>'
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
    r = requests.post(f"{url}", form_data, verify=False, cookies = {'CONSENT' : 'YES+'})

    html = str(r.content)

    # Is there a brief profile (detail page containing chemical properties)?
    search_str = "https://echa.europa.eu/en/brief-profile/-/briefprofile/"

    start = html.find(search_str)

    if start > 0:
        finish = html.find("\"", start)
        if finish > 0:
            doc = html[start + len(search_str): finish]

            detail_page = html[start: finish]

            r = requests.get(f"{detail_page}", verify=False, cookies = {'CONSENT' : 'YES+'})

            # strip unwanted caracters to make property search easier (without using specialized libraries)
            html = str(r.content).replace("\\n","").replace("\\r","").replace("\\t","").replace("b\'","").replace("\'","").replace("&#xb0;","").replace("&nbsp;"," ")
            html = re.sub(" +", " ", html).replace("> ",">").replace(" <","<")

            results = ""

            for property in properties:
                property['property_value'] = get_cas_property(html, property['property_search_string'])
                if property['property_value'] == "" and  property['property_search_string_2'] != "":
                    property['property_value'] = get_cas_property(html, property['property_search_string_2'])

                results += f"{property['property_name']}: {property['property_value']}\n"

        return results

    return "CAS profile not found"