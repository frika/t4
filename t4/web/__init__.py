##  This file is part of the t4 Python module collection. 
##
##  Copyright 2011 by Diedrich Vorberg <diedrich@tux4web.de>
##
##  All Rights Reserved
##
##  For more Information on orm see the README file.
##
##  This program is free software; you can redistribute it and/or modify
##  it under the terms of the GNU General Public License as published by
##  the Free Software Foundation; either version 2 of the License, or
##  (at your option) any later version.
##
##  This program is distributed in the hope that it will be useful,
##  but WITHOUT ANY WARRANTY; without even the implied warranty of
##  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##  GNU General Public License for more details.
##
##  You should have received a copy of the GNU General Public License
##  along with this program; if not, write to the Free Software
##  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
##
##  I have added a copy of the GPL in the file COPYING


import json, urllib, urlparse, tempfile, time
from title_to_id import title_to_id
from html_length import html_length, html_area
from typography import *

def js_string_literal(s):
    return json.dumps(s)

def add_url_param(url, params={}):
    params = urllib.urlencode(params)
    if "?" in url:
        return url + "&" + params
    else:
        return url + "?" + params

def set_url_param(url, params={}):
    url = urlparse.urlparse(url)
    query = urlparse.parse_qs(url.query)
    for key, value in query.items():
        if len(value) == 1:
            query[key] = value[0]
    query.update(params)
    
    for key, value in params.items():
        if value is None:
            del query[key]
            
    return "%s://%s%s?%s" % (url.scheme, url.netloc, url.path,
                             urllib.urlencode(query),)

def html2txt(html):
    """
    Uses lynx to dump `html` to a text-only representation.
    """
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as fp:
        try:
            fp.write(html)
            fp.close()
        
            pipe = os.popen("lynx -dump %s" % fp.name, "r")
            return pipe.read()
        finally:
            os.unlink(fp.name)
        
