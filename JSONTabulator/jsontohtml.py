from json2html import *
input = {
  "Transaction ID": "1234678910",
  "Products": [
    {
      "Product ID": "9I879871",
      "Product Name": "Nasi Goreng",
      "Price": 15000
    },
    {
      "Product ID": "987986",
      "Product Name": "Bakso Kuah",
      "Price": 70000
    },
    {
      "Product ID": "46546542333",
      "Product Name": "Martabak Keju",
      "Price": 54000
    }
  ]
};
print(json2html.convert(json = input))