# VA: Town Hall robots.txt clarification

**To:** Virginia Regulatory Town Hall administrators (Department of Planning and Budget). Use the
Town Hall contact page; no address was confirmed during the rights check.
**Subject:** Question about Town Hall robots.txt

Hello,

I'm building DocketClock, a service that helps the public find comment periods and hearings and
their deadlines, with a link back to the official source.

Town Hall's robots.txt contains `Disallow: /L./` and `Disallow: /l./`. Are these meant to cover the
`/L/` listing pages (for example the comment forums and meeting listings)? If those pages are open
to automated reading, we'd read them at most once every 5 seconds, as your Crawl-delay asks, with
an identifying user agent. If not, we'll keep to the Virginia Register and its RSS feed.

Thank you,
Lucas Homer
