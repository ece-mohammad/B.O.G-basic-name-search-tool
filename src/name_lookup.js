const axios = require('axios');

// Function to split the name into different variations
function getNameVariations(fullName) {
    const names = fullName.split(' ');
    if(names.length===1)    return [fullName];
    return [
        names[names.length - 1], // Last name
        names.slice(-2).join(' '), // Last two names
        names[0] + ' ' + names[names.length - 1], // First and last name
        names[0], // First and last name
        fullName // Full name
    ];
}

// Function to search a URL with the last name
async function searchURL(url, lastName) {
    try {
        const response = await axios.get(url + encodeURIComponent(lastName));
        return response.data;
    } catch (error) {
        console.error(`Error fetching ${url}: ${error}`);
        return null;
    }
}

// Function to count occurrences of each term in a string
function countOccurrences(text, terms) {
    let counts = {};
    for (let term of terms) {
        const regex = new RegExp(term, 'gi'); // 'gi' for global, case-insensitive
        counts[term] = (text.match(regex) || []).length;
    }
    return counts;
}

// Main function to execute the script
async function main(name) {
    const nameVariations = getNameVariations(name);
    const uniqueVariations = [...new Set(nameVariations)];
    const lastName = nameVariations[0];
    const urls = [
        'https://airwars.org/civilian-casualties/?belligerent=israeli-military&start_date=2023-10-07&country=the-gaza-strip&search=',
        'https://www.aintnumbers.com/?s=',
    ];

    let results = {};
    console.log("Unique variations", uniqueVariations)

    for (const url of urls) {
        const html = await searchURL(url, lastName);
        if (html) {
            results[url] = countOccurrences(html, uniqueVariations);
        } else {
            results[url] = { error: 'Error fetching data' };
        }
    }

    // Display the results
    console.log(`Results for variations of "${name}":`);
    for (const [url, counts] of Object.entries(results)) {
        console.log(`\nURL: ${url}${lastName}`);
        console.table(counts);
    }
}

// Get the name argument from the command line
if (process.argv.length < 3) {
    console.log("Please provide a name as an argument.");
} else {
    const nameArgument = process.argv[2];
    main(nameArgument);
}
