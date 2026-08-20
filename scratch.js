const fs = require('fs');
const content = fs.readFileSync('asset.html', 'utf8');

const regex = /body\.value = `([^`]+)`/;
const match = content.match(regex);
if (!match) {
    console.log("No match found");
    process.exit(1);
}

const lines = match[1].split('\n');

const tabWidth = 8;
const alignCols = [];

lines.forEach((line, i) => {
    if (line.includes(':')) {
        const parts = line.split(':');
        const prefix = parts[0];
        if (prefix.trim() === '') return; // Skip lines starting with colon
        
        let visualLength = 0;
        for (let j = 0; j < prefix.length; j++) {
            if (prefix[j] === '\t') {
                visualLength += tabWidth - (visualLength % tabWidth);
            } else {
                visualLength += 1;
            }
        }
        alignCols.push({ lineNum: i + 1, originalPrefix: prefix.replace(/\t/g, '\\t'), visualLength });
    }
});

console.log(JSON.stringify(alignCols, null, 2));
