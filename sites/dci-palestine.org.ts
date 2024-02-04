import puppeteer from 'puppeteer-extra'
import hidden from 'puppeteer-extra-plugin-stealth'
// require executablePath from puppeteer
import { executablePath } from 'puppeteer'
import { JSDOM } from 'jsdom'
const root = 'https://www.dci-palestine.org/tags/fatalities_and_injuries'

const example_div = `
<div class="span6 featured">
  <div class="featured-pic">
    <a href="/israeli_settler_soldier_shoot_dead_17_year_old_palestinian_american_boy"><img src="https://assets.nationbuilder.com/dcipalestine/pages/5848/attachments/original/1705761985/Tawfiq_hero.png?1705761985"></a>
  </div>
     <script type="text/javascript"></script>
  <div class="featured-content">
    <span class="date">
      January 20, 2024 
     - Location:
      <a href="/tags/west_bank">West Bank</a>
        Issue:
      <a href="/tags/news">News</a>
       -                 
      <a href="/tags/settler_and_soldier_violence">Settler and Soldier Violence</a>
       -                 
      <a href="/tags/fatalities_and_injuries">Fatalities and Injuries</a>
    </span>
    <h3><a href="/israeli_settler_soldier_shoot_dead_17_year_old_palestinian_american_boy">Israeli settler, soldier shoot dead 17-year-old Palestinian-American boy</a></h3> 
  </div>    
</div>
`

const testSpan = `\n      January 05, 2024 \n     - Location:\n      \n      \n      \n\n\n      \n\n      \n\n\n      \n      \n       \n      \t\t\n      \t\t\n                      \n      \n      \n      \n        \n      \t\t\n        \n      \t\t\n      \t\t\n                      \n      \n                      
`

const firstLine = /.*(?=-)/
const dateRx = new RegExp(firstLine)
const getDate = (dateString) => {
    const clean = dateString.replace(/\s{2,}|,/g, '')
    const dateMatch = dateRx.exec(clean)
    //console.log('dateMatch', dateMatch)
    return dateMatch ? dateMatch[0].trim() : ''
}

//getDate(testSpan) //?
const months = [
    'January',
    'February',
    'March',
    'April',
    'May',
    'June',
    'July',
    'August',
    'September',
    'October',
    'November',
    'December',
]
async function grab(pageNumber) {
    puppeteer.use(hidden())
    const browser = await puppeteer.launch({
        args: ['--no-sandbox'],
        headless: 'new',
        ignoreHTTPSErrors: true,
        executablePath: executablePath(),
    })

    const page = await browser.newPage()
    //await page.setViewport({
    //    width: 1920,
    //    height: 1280,
    //    deviceScaleFactor: 1,
    //})

    await page.goto(`${root}?page=${pageNumber}`, {
        waitUntil: 'networkidle0',
    })

    const links = (await page.evaluate(() => {
        const articleLinkClass = 'span6 featured'
        const articleLinks = document.getElementsByClassName(articleLinkClass)
        const articles = [] as any[]
        try {
            for (let i = 0; i < articleLinks.length; i++) {
                const article = articleLinks[i]
                const link = article.getElementsByTagName('a')[0].href
                const date_string =
                    article.getElementsByClassName('date')[0]?.firstChild?.textContent
                const headline = article.getElementsByTagName('h3')[0].textContent || ''
                const payload = {
                    date_string,
                    headline,
                    link,
                }

                articles.push(payload)
            }
            return articles
        } catch (error) {
            //console.log('error', error)
        }
    })) as any[]

    // regex over each of the date_strings in the payloads
    // and get the date
    const payloads = links.reduce((acc, link) => {
        const { date_string, ...rest } = link
        const date = getDate(date_string)
        const [month, day, year] = date.split(' ')
        const yearInt = parseInt(year)
        // only get articles that are on after October 2023
        if (yearInt > 2023 || (yearInt === 2023 && months.indexOf(month) > 8)) {
            return acc.concat({ ...rest, date })
        } else {
            return acc
        }
    }, [] as any[])

    await browser.close()
    return payloads
}

grab(1).then(console.log) // should return an array of links to the articles on the first page

const goToPagesAndScrape = async (pageNumber) => {
    const list = await grab(pageNumber)
    const
}

/**
 * Here is the root of the site
 * https://www.dci-palestine.org/tags/fatalities_and_injuries?page=1
 *
 * I want to scrape the page and click on the next page
 */
const scrape = async (page) => {
    const dom = await new JSDOM(page)
    const document = dom.window.document
    const articleLinkClass = 'span6 featured'
    const articleLinks = document.getElementsByClassName(articleLinkClass)
    const articles = [] as any[]
    for (let i = 0; i < articleLinks.length; i++) {
        const article = articleLinks[i]
        const link = article.getElementsByTagName('a')[0].href
        articles.push(link)
    }
    return articles
}

// test
