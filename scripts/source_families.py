#!/usr/bin/env python3
"""Shared publisher-family normalization for independent-source accounting."""
SOURCE_FAMILIES={
 'Fox News':'fox','Fox News Politics':'fox','Fox News World':'fox','Fox Business':'fox',
 'National Review':'national-review','National Review The Corner':'national-review',
 'The Daily Signal':'daily-signal','Daily Signal':'daily-signal','The Daily Signal Politics':'daily-signal','Daily Signal Politics':'daily-signal',
 'RealClearPolitics':'realclear','RealClearPolicy':'realclear','RealClearWorld':'realclear','RealClearDefense':'realclear',
 'Associated Press':'ap','AP':'ap','Reuters':'reuters','NPR News':'npr','NPR Culture':'npr','NPR':'npr',
 'CBS News':'cbs','CBS Sports':'cbs','ABC News':'abc','NBC News':'nbc','CNN':'cnn',
 'BBC News':'bbc','BBC Sport':'bbc','BBC Sports':'bbc','BBC Entertainment':'bbc','BBC Science':'bbc',
 'New York Post':'new-york-post','Page Six':'new-york-post','New York Times':'new-york-times','Washington Post':'washington-post',
 'Stars and Stripes':'stars-and-stripes','Stars and Stripes Storm Tracker':'stars-and-stripes',
 'Axios':'axios','Politico':'politico','Breitbart':'breitbart','Daily Caller':'daily-caller','Daily Wire':'daily-wire','Hot Air':'hot-air','National Pulse':'national-pulse','RedState':'redstate','WND':'wnd',
 'Washington Times':'washington-times','Washington Examiner':'washington-examiner','Newsmax':'newsmax','The Blaze':'blaze','Washington Free Beacon':'free-beacon','The Federalist':'federalist','Townhall':'townhall','PJ Media':'pj-media','American Thinker':'american-thinker','Commentary Magazine':'commentary','American Spectator':'american-spectator','Twitchy':'twitchy','LifeSiteNews':'lifesitenews','The Epoch Times':'epoch-times','Human Events':'human-events','The College Fix':'college-fix','Legal Insurrection':'legal-insurrection','Just the News':'just-the-news',
 'Reason':'reason','The American Conservative':'american-conservative','City Journal':'city-journal','American Greatness':'american-greatness','The Post Millennial':'post-millennial','Western Journal':'western-journal','Power Line':'power-line','The Spectator World':'spectator-world','The Dispatch':'dispatch','The Daily Economy':'daily-economy','Foundation for Economic Education':'fee','Cato Institute':'cato','Heritage Foundation':'heritage','Judicial Watch':'judicial-watch',
 'The Hill':'the-hill','SCOTUSblog':'scotusblog','Defense News':'defense-news','SpaceNews':'spacenews','Ars Technica':'ars-technica'
}

def family(source):
 return SOURCE_FAMILIES.get(str(source or '').strip(),str(source or '').strip().lower() or 'unknown')
