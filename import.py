import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def main():
    f = open("books.csv")
    reader = csv.reader(f)
    for isbn, title, author, pub_year in reader:
        db.execute("INSERT INTO books_info (isbn, title, author, pub_year) VALUES (:isbn, :title, :author, :pub_year)",
                    {"isbn": isbn, "title": title, "author": author, "pub_year": pub_year})
        print(f"Added books of isbn:{isbn} ,title:{title} written by {author} from {pub_year}.")
    db.commit()

if __name__ == "__main__":
    main()
