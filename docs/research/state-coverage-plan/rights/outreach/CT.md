# CT: JSON route inquiry

**To:** Eregs.Support@ct.gov (eRegulations Division, from the About Us page)
**Subject:** Question about reading open comment periods from eRegulations

Hello,

I'm building DocketClock, a service that helps the public find comment periods and hearings and
their deadlines, with a link back to the official source.

The eRegulations portal loads its open comment periods from
`/eRegsPortal/Browse/getOpenCommentPeriods`. May an outside service read that endpoint, at most one
request every 5 seconds with an identifying user agent? If you'd prefer we use the rendered pages,
the e-mail notification service or something else, we'll do that. Is there anything we should know
about its stability or planned changes?

Thank you,
Lucas Homer
