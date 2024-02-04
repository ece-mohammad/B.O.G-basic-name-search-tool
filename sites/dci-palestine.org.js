import { JSDOM } from 'jsdom'
import { promises, readFileSync } from 'fs'
import openai from 'openai'
import dotenv from 'dotenv'

dotenv.config()

const root = 'https://www.dci-palestine.org/tags/fatalities_and_injuries'

// save the html
export const fetchHTML = async (page = 1) => {
    const res = await fetch(`${root}?page=${page}`)

    const html = await res.text()
    await promises.writeFile(`./dci.html`, html)
    return html
}

//export const grabArticles = async (page = 1) => {
//    const html = await fetchHTML(page)
//    const dom = new JSDOM(html)
//    const { document } = dom.window
//    const articleLinkClass = '.span6'

//    console.log(document.querySelector(articleLinkClass))
//}

//grabArticles().then(console.log)

const firstLine = /.*(?=-)/
const dateRx = new RegExp(firstLine)
const getDate = (dateString) => {
    const clean = dateString.replace(/\s{2,}|,/g, '')
    const dateMatch = dateRx.exec(clean)
    //console.log('dateMatch', dateMatch)
    return dateMatch ? dateMatch[0].trim() : ''
}

const file = readFileSync('./dci.html', 'utf8')

const getLinksFromRoot = async (html) => {
    const dom = new JSDOM(html)

    // @ts-ignore
    const { document } = dom.window

    const articleLinkClass = '.featured'

    const articles = document.querySelectorAll(articleLinkClass)

    let done = false
    const articleLinks = Array.from(articles).reduce((acc, article) => {
        const _link = article.querySelector('a')
        const headline = article?.querySelector('h3')?.textContent?.trim()
        const dateDirty = article.getElementsByClassName('date')[0]?.firstChild?.textContent
        const apex = root.split('/').slice(0, 3).join('/')
        const link = apex + _link?.getAttribute('href') || ''
        const date = getDate(dateDirty)
        const dateObj = new Date(date)
        // if date is greater than October 1, 2023
        if (dateObj > new Date('October 1, 2023')) {
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

getPageAndConvertToText('2024/January/1822841312.html').then(async (text) => {
    const response = await callClosedAi({ text })
    console.log({ text, data: response })
    // write response to test file
    const testFileName = `./test/llm-payload.json`
    await promises.writeFile(testFileName, JSON.stringify({ text, data: response }, null, 2))
})

const getPageAndConvertToData = async (file) => {
    const html = readFileSync(file, 'utf8')
    const text = await htmlToText(html)
    const response = await callClosedAi({ text })
    return response
}

// grab all the html files from each link and store them in a directorty with the year/month as the directory
const getArticles = async (links) => {
    const articles = await Promise.all(
        links
            .map(async (payload) => {
                const { link, headline, date } = payload
                // if the lowercased headline contains any of the keywords
                if (keywords.some((word) => headline.toLowerCase().includes(word))) {
                    const hashed = hash(headline)
                    // save the html
                    const _date = new Date(date)
                    const year = _date.getFullYear()
                    // get month name
                    const month = _date.toLocaleString('default', { month: 'long' })
                    const day = _date.getDate()
                    const dir = `${year}/${month}`

                    const htmlFile = `${dir}/${hashed}.html`
                    const metaFile = `${dir}/${hashed}.json`
                    // get the data
                    let data = { arguments: null, name: null }
                    try {
                        data = (await getPageAndConvertToData(htmlFile)) || {
                            arguments: null,
                            name: null,
                        }
                    } catch (e) {
                        console.error(`Error getting victims from closedai: ${e}`)
                    }
                    // if the file already exists, don't scrape it it
                    const victims = data['arguments']
                    try {
                        await promises.access(htmlFile)
                        return { headline, date, link, htmlFile, victims }
                    } catch (e) {
                        //console.log('file does not exist')

                        const res = await fetch(link)
                        const html = await res.text()

                        await promises.mkdir(dir, { recursive: true })
                        await promises.writeFile(htmlFile, html)
                        await promises.writeFile(
                            metaFile,
                            JSON.stringify({ headline, date, link, victims })
                        )
                        return { headline, date, link, htmlFile, victims }
                    }
                } else {
                    return null
                }
            })
            .filter((article) => article !== null)
    )
    return articles
}

const getArticlesByPage = async (file) => {
    const linksForPage = await getLinksFromRoot(file)
    const articlesForPage = await getArticles(linksForPage)
    // save the articles as a separate file
    const dir = `./test`
    await promises.mkdir(dir, { recursive: true })
    await promises.writeFile(`${dir}/page1.json`, JSON.stringify(articlesForPage))
    return articlesForPage
}

getArticlesByPage(file).then(console.log)
//console.log(text)
