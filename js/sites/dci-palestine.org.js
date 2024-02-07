import { JSDOM } from 'jsdom'
import { promises, readFileSync } from 'fs'
import dotenv from 'dotenv'
import { scrapePage } from '../utils/headless.js'

dotenv.config()

const root = 'https://www.dci-palestine.org/tags/fatalities_and_injuries'

let done = false
// save the html
export const fetchHTML = async (url = root) => {
    try {
        const res = await fetch(url)

        let html = await res.text()
        if (html) {
            console.log(`Fetched page: ${url}`)
        } else {
            html = await scrapePage(url)
            console.log(`Scraped page ${url}`)
        }
        html = html.replace(/<style([\s\S]*?)<\/style>/gm, '')
        html = html.replace(/<script([\s\S]*?)<\/script>/gm, '')
        // replace more than one newline with a single newline (plus any trailing whitespace)
        html = html.replace(/\n\s*\n/g, '')
        return html
    } catch (e) {
        console.error(`Error fetching page ${url}: ${e}`)
        return ''
    }
}

export const grabArticles = async ({ page = 1, source = root }) => {
    let html = null
    html = await fetchHTML(`${source}?page=${page}`)
    const dom = new JSDOM(html)
    const { document } = dom.window
    const articleLinkClass = '.span6'

    const articles = document.querySelector(articleLinkClass)
    dom.window.close()
    return articles
}

//grabArticles({ page: 2 }).then(console.log)
const getDate = (dateString) => {
    const firstLine = /.*(?=-)/
    const dateRx = new RegExp(firstLine)
    const clean = dateString.replace(/\s{2,}/g, '')
    const dateMatch = dateRx.exec(clean)
    //console.log('dateMatch', dateMatch)
    const date = dateMatch ? dateMatch[0].trim() : ''
    return date
}

//const file = readFileSync('./dci.html', 'utf8')

const getDciLinksFromLanding = async (html) => {
    const dom = new JSDOM(html)

    // @ts-ignore
    const { document } = dom.window

    const articleLinkClass = '.featured'

    const articles = document.querySelectorAll(articleLinkClass)

    const articleLinks = Array.from(articles).reduce((acc, article) => {
        const _link = article.querySelector('a')
        const headline = article?.querySelector('h3')?.textContent?.trim()
        const dateDirty = article.getElementsByClassName('date')[0]?.firstChild?.textContent
        const apex = root.split('/').slice(0, 3).join('/')
        const link = apex + _link?.getAttribute('href') || ''
        const date = getDate(dateDirty)
        const dateObj = new Date(date)
        // if date is greater than October 1, 2023
        const relevant = dateObj.getTime() > new Date('October 1, 2023').getTime()
        //console.log({ relevant })
        if (relevant) {
            // @ts-ignore
            return acc.concat({ link, headline, date })
        } else {
            done = true
            console.log({ done })
            return acc
        }
    }, [])
    // close jsdom
    dom.window.close()
    return articleLinks
}

//const text = articles[0].textContent
//getLinksFromRoot(file).then(console.log)

const hash = (str) => {
    let hash = 0
    for (let i = 0; i < str.length; i++) {
        let char = str.charCodeAt(i)
        hash = (hash << 5) - hash + char
        hash = hash & hash // Convert to 32bit integer
    }
    return hash
}

const keywords = [
    'shoot',
    'shot',
    'kill',
    'murder',
    'martyr',
    'fire',
    'weapon',
    'dead',
    'died',
    'death',
    'injur',
    'wound',
    'hurt',
    'casualt',
    'fatal',
    'bomb',
    'explo',
    'strike',
    'attack',
    'viol',
]

const promptGetNamesArray = `
You are a helpful assistant. Your job is to get the names, dates of death, age, sex, and location of death of the victims mentioned in the page. 
If you don't have a specific name for the victim, don't return an entry for that victim. It's important to get the ages of the victims.
`

const get_victims = {
    type: 'function',
    function: {
        name: 'get_victims',
        description:
            'Get the names, dates of death, and location of death of the victims mentioned in the page.',
        parameters: {
            type: 'object',
            properties: {
                results: {
                    type: 'array',
                    items: {
                        type: 'object',
                        required: ['name', 'dod', 'location', 'age'],
                        properties: {
                            name: {
                                type: 'string',
                                description: 'The name of the victim',
                            },
                            dod: {
                                type: 'string',
                                description:
                                    'The date of death of the victim, e.g., January 1, 2023',
                            },
                            location: {
                                type: 'string',
                                description: 'The location of death of the victim',
                            },
                            age: {
                                type: 'string',
                                description: 'The age of the victim at the time of death',
                            },
                            sex: {
                                type: 'string',
                                description: 'The sex of the victim',
                            },
                        },
                    },
                },
            },
        },
    },
}

const callClosedAi = async ({ text, prompt = promptGetNamesArray, tools = [get_victims] }) => {
    const api_key = process.env.OPENAI_API_KEY
    console.log({ api_key })
    const {
        type,
        function: { name },
    } = tools[0]
    try {
        const url = 'https://api.openai.com/v1/chat/completions'

        const response = await fetch(url, {
            body: JSON.stringify({
                model: 'gpt-3.5-turbo',
                messages: [
                    {
                        role: 'system',
                        content: prompt,
                    },
                    {
                        role: 'user',
                        content: text,
                    },
                ],
                temperature: 0,
                max_tokens: 2000,
                ...(tools && {
                    tools,
                    tool_choice: {
                        type,
                        function: { name },
                    },
                }),

                //tool_choice: 'auto',
            }),
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: 'Bearer ' + api_key,
            },
        }).then((response) => {
            if (response.ok) {
                return response.json().then((json) => {
                    //console.log({ json })
                    const tool_calls = json.choices[0].message.tool_calls
                    //console.log({ tool_calls })
                    const { name, arguments: args } = tool_calls[0].function
                    const { results } = JSON.parse(args)
                    console.log({ name, results })
                    return { name, arguments: results }
                })
            } else {
                console.error('Error: ', response.status, response.statusText)
            }
        })
        return response
    } catch (err) {
        console.error(`Error: ${err}`)
    }
}

const clean = (str) => str.replace(/\s{2,}/g, ' ').trim()

// grab a sample page file, convert html to text
const htmlToText = async (html) => {
    // convert html to plain text
    const dom = new JSDOM(html)
    const { document } = dom.window
    // remove all scripts
    const scripts = document.querySelectorAll('script')
    scripts.forEach((script) => script.remove())
    // remove all css
    const styles = document.querySelectorAll('style')
    styles.forEach((style) => style.remove())
    const text = document.querySelector('.content-box')?.textContent
    dom.window.close()
    const cleaned = clean(text)
    //console.log({ cleaned })
    return cleaned
}

const getPageAndConvertToText = async (file) => {
    const html = readFileSync(file, 'utf8')
    return await htmlToText(html)
}

//getPageAndConvertToText('2024/January/1822841312.html').then(async (text) => {
//    const response = await callClosedAi({ text })
//    console.log({ text, data: response })
//    // write response to test file
//    const testFileName = `./test/llm-payload.json`
//    await promises.writeFile(testFileName, JSON.stringify({ text, data: response }, null, 2))
//})

const getPageAndConvertToData = async (html) => {
    const text = await htmlToText(html)
    const response = await callClosedAi({ text })
    return response
}

// grab all the html files from each link and store them in a directorty with the year/month as the directory
const getAndStoreArticlesFromLinks = async (links) => {
    const articles = await links.reduce(async (acc, payload) => {
        const _acc = await acc
        const { link, headline, date } = payload
        // if the lowercased headline contains any of the keywords
        if (keywords.some((word) => headline.toLowerCase().includes(word))) {
            const hashed = hash(headline)
            // save the html
            const _date = new Date(date)
            const year = _date.getFullYear()
            // get month name
            const month = _date.toLocaleString('default', { month: 'long' })
            const dir = `${year}/${month}`

            // get the data
            let data = { arguments: null, name: null }
            const htmlFile = `${dir}/${hashed}.html`
            const metaFile = `${dir}/${hashed}.json`
            try {
                const file = await promises.readFile(metaFile, 'utf8')
                console.log(`File exists for ${headline}`)
                const { victims } = JSON.parse(file)
                if (victims) {
                    console.log(`Victims already exist for file: ${htmlFile}`)
                    return _acc.concat({ headline, date, link, htmlFile, victims })
                } else {
                    throw new Error('No victims for file yet. Grabbing...')
                }
            } catch (e) {
                console.log(`Getting victim data for headline: ${headline}`)
                const html = await fetchHTML(link)
                try {
                    data = (await getPageAndConvertToData(html)) || {
                        arguments: null,
                        name: null,
                    }
                } catch (e) {
                    console.error(`Error getting victims from closedai: ${e}`)
                }
                // if the file already exists, don't scrape it it
                const victims = data['arguments']
                //console.log('file does not exist')

                await promises.mkdir(dir, { recursive: true })
                await promises.writeFile(htmlFile, html)
                await promises.writeFile(
                    metaFile,
                    JSON.stringify({ headline, date, link, htmlFile, victims }, null, 2)
                )
                return _acc.concat({ headline, date, link, htmlFile, victims })
            }
        } else {
            console.log(`No keywords in headline: ${headline}. Skipping.`)
            return _acc
        }
    }, Promise.resolve([]))

    return articles
}

const getArticlesByPage = async (file) => {
    const linksForPage = await getDciLinksFromLanding(file)
    const articlesForPage = await getAndStoreArticlesFromLinks(linksForPage)
    // save the articles as a separate file
    const dir = `./test`
    await promises.mkdir(dir, { recursive: true })
    await promises.writeFile(`${dir}/page1.json`, JSON.stringify(articlesForPage))
    return articlesForPage
}

//getArticlesByPage(file).then(console.log)
// recursively get all the articles from the site, stopping when done is true
const getArticlesRecursively = async ({ page = 1, acc = [], source = root, stop = 2 }) => {
    const domain = source.split('/')[2]
    const dir = `./sources/${domain}`
    const article = source.split('/').slice(-1)[0]
    if (!done && page <= stop) {
        // throttle with timeout
        const file = `./sources/${domain}/${article}?page=${page}.html`
        await new Promise((resolve) => setTimeout(resolve, 1000))
        let html = null
        try {
            html = await promises.readFile(file, 'utf8')
        } catch (e) {
            console.log(`No existing file for ${source}, scraping...`)
            //if (page > 1) {
            html = await fetchHTML(`${source}?page=${page}`)
            //} else {
            //    html = await fetchHTML(source)
            //}
        }
        // sets done to true if the date is less than October 1, 2023
        if (html) {
            const linksForPage = await getDciLinksFromLanding(html)
            console.log({ links: linksForPage.length })
            const articlesForPage = await getAndStoreArticlesFromLinks(linksForPage)
            console.log({ articles: articlesForPage.length })
            // save the articles as a separate file

            await promises.mkdir(dir, { recursive: true })
            await promises.writeFile(
                `${dir}/page_${page}.json`,
                JSON.stringify(articlesForPage, null, 2)
            )
            await promises.writeFile(file, html)
            return getArticlesRecursively({
                page: page + 1,
                acc: acc.concat(articlesForPage),
                source,
                stop,
            })
        } else {
            return acc
        }
    } else {
        await promises.writeFile(`${dir}/all.json`, JSON.stringify(acc, null, 2))
        return acc
    }
}

getArticlesRecursively({ page: 1, stop: 3 }).then((r) =>
    console.log('total articles parsed: ', r.length)
)
