This is a study project to learn more about web programming using HTML, a bit of JavaScrip, and Python using Flask

It is a webSite where you can register login (the site even saves cookies for remembering sessions).
The accounts started with a fixed amout of cash when created (stored in the finance database) and can spend that cash "buying" stocks or gain cash "selling" stocks.
All the "transactions" on the site are not real and meant just to learn storing user data in the databases.
The site only checks that stock price and the current time using the IEX Cloud(*unfortunatly the service used in this code was updated and no longer supports this application)
Using only that price info (ignoring a lot of the complicated situation of the stock market) in subtracts from the users ballance and adds the stock to the users wallet
It does the same logic but reversed when a user sells stocks
