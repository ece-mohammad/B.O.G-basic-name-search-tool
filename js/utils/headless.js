import pup from 'puppeteer-extra'
import stealth from 'puppeteer-extra-plugin-stealth'
import fs from 'fs'
import AdblockerPlugin from 'puppeteer-extra-plugin-adblocker'
const stealthMode = stealth()

stealthMode.enabledEvasions.delete(`chrome.runtime`)
stealthMode.enabledEvasions.delete(`iframe.contentWindow`)
/**
 * takes a url and a page and scrapes the content of that page
 */
pup.use(AdblockerPlugin({ blockTrackers: true }))
pup.use(stealthMode)
export async function scrapePage(url, loadedSelector = '.main-container') {
    const browser = await pup.launch({
        headless: false, //'new',
        ignoreHTTPSErrors: true,

        devtools: false,
        // devtools: true,

        timeout: 60000,
        slowMo: 0,

        defaultViewport: null,

        pipe: false,
        dumpio: false,

        handleSIGINT: true,
        handleSIGTERM: true,
        handleSIGHUP: true,

        args: [
            // chrome://gpu
            // `--single-process`,

            `--no-zygote`,
            `--no-sandbox`,
            `--disable-setuid-sandbox`,
            `--disable-web-security`,
            `--ignore-certifcate-errors`,
            `--ignore-certifcate-errors-spki-list`,
            `--disable-features=IsolateOrigins,site-per-process`,
            `--disable-site-isolation-trials`,

            `--disable-blink-features`,
            `--disable-blink-features=AutomationControlled`,

            `--no-default-browser-check`,
            `--no-first-run`,
            `--disable-infobars`,
            `--disable-notifications`,
            `--disable-desktop-notifications`,
            `--hide-scrollbars`,
            `--mute-audio`,

            `--window-position=0,0`,
            `--window-size=1920,1080`,

            `--font-render-hinting=none`,
            `--disable-gpu`,
            `--disable-gpu-sandbox`,
            `--disable-dev-shm-usage`,
            `--disable-software-rasterizer`,
            `--enable-low-res-tiling`,
            `--disable-accelerated-2d-canvas`,
            `--disable-canvas-aa`,
            `--disable-2d-canvas-clip-aa`,
            `--disable-gl-drawing-for-tests`,

            // `--kiosk`,

            `--disable-background-timer-throttling`,
            `--disable-backgrounding-occluded-windows`,
            `--disable-breakpad`,
            `--disable-client-side-phishing-detection`,
            `--disable-component-extensions-with-background-pages`,
            `--disable-default-apps`,
            `--disable-dev-shm-usage`,
            `--disable-extensions`,
            `--disable-features=TranslateUI`,
            `--disable-hang-monitor`,
            `--disable-ipc-flooding-protection`,
            `--disable-popup-blocking`,
            `--disable-prompt-on-repost`,
            `--disable-renderer-backgrounding`,
            `--disable-sync`,
            `--force-color-profile=srgb`,
            `--metrics-recording-only`,

            `--disable-webgl`,
            `--disable-webgl2`,
            `--disable-gpu-compositing`,
        ],

        ignoreDefaultArgs: [`--enable-automation`],
    })
    const page = await browser.newPage()

    await page.setRequestInterception(true)
    //page.on('request', (request) => {
    //    if (['stylesheet', 'font', 'image', 'script'].indexOf(request.resourceType()) !== -1) {
    //        request.abort()
    //    } else {
    //        request.continue()
    //    }
    //})
    // keep page open for 5 seconds

    const userAgent = await page.evaluate(() => navigator.userAgent)

    // If everything correct then no 'HeadlessChrome' sub string on userAgent
    console.log(userAgent)

    await page.goto(url)

    await page.waitForSelector(loadedSelector, { timeout: 5000 })
    let content = await page.content()
    console.log({ content })
    await browser.close()
    // remove style and script nodes
    return content
}
//const root = 'https://www.dci-palestine.org/tags/fatalities_and_injuries'

//scrapePage(root, 1).then(console.log)
