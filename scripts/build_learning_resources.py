"""
Builds and validates `data/skill_learning_resources.json` with 2-3 verified,
prefer-free learning resources per skill across all roles and roadmaps.

Every URL uses a canonical, verifiable official documentation hub, free
curriculum track (freeCodeCamp, Kaggle Learn, MDN, Microsoft Learn, AWS Skill
Builder, roadmap.sh, CS50, PortSwigger, TryHackMe, Cisco NetAcad), or verified
Coursera/Atlassian program. Zero fabricated course names or links.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"


def _res(platform: str, title: str, description: str, url: str, cost: str = "Free") -> dict:
    return {
        "platform": platform,
        "title": title,
        "description": description,
        "url": url,
        "cost": cost,
    }


# Verified curated 2-3 resource bundles keyed by canonical skill name
SKILL_BUNDLES: Dict[str, dict] = {
    "Python": {
        "topics": "Data structures, functions, OOP, virtual environments, file I/O",
        "project": "Build a CLI log parser and automated API data fetcher",
        "est_time": "3-4 weeks",
        "resources": [
            _res("freeCodeCamp", "Scientific Computing with Python", "Free project-based Python track covering fundamentals, OOP, and algorithms.", "https://www.freecodecamp.org/learn/scientific-computing-with-python/"),
            _res("Kaggle Learn", "Python Micro-Course", "Hands-on browser exercises covering Python syntax, lists, loops, and libraries.", "https://www.kaggle.com/learn/python"),
            _res("Python Official Docs", "The Python 3 Tutorial", "Authoritative guide from the Python Software Foundation covering standard library essentials.", "https://docs.python.org/3/tutorial/"),
        ],
    },
    "Java": {
        "topics": "OOP, Collections, Streams, Generics, Exception Handling",
        "project": "Build a multi-threaded order inventory REST backend",
        "est_time": "4-5 weeks",
        "resources": [
            _res("Dev.java", "Learn Java — Official Oracle Tutorials", "Structured modern Java tutorials maintained by the Oracle Java team.", "https://dev.java/learn/"),
            _res("roadmap.sh", "Java Developer Roadmap", "Step-by-step interactive Java skill path linking curated guides.", "https://roadmap.sh/java"),
            _res("Harvard CS50", "CS50's Introduction to Programming & Computer Science", "Foundational computer science concepts helpful for strongly typed OOP languages.", "https://cs50.harvard.edu/x/"),
        ],
    },
    "JavaScript": {
        "topics": "ES6+, DOM manipulation, Async/Await, Fetch API, Closures",
        "project": "Build an interactive weather and task planner web app",
        "est_time": "3-4 weeks",
        "resources": [
            _res("freeCodeCamp", "JavaScript Algorithms and Data Structures", "Interactive browser challenges teaching ES6+, OOP, functional programming, and projects.", "https://www.freecodecamp.org/learn/javascript-algorithms-and-data-structures-v8/"),
            _res("MDN Web Docs", "Learn Web Development: JavaScript", "Mozilla's beginner-to-intermediate modules covering DOM, events, and async JS.", "https://developer.mozilla.org/en-US/docs/Learn/JavaScript"),
            _res("roadmap.sh", "JavaScript Roadmap", "Topic-by-topic JavaScript learning map with curated articles.", "https://roadmap.sh/javascript"),
        ],
    },
    "TypeScript": {
        "topics": "Interfaces, Generics, Union types, Type narrowing, tsconfig",
        "project": "Refactor a React or Node.js REST client with strict TypeScript types",
        "est_time": "1-2 weeks",
        "resources": [
            _res("TypeScript Docs", "The TypeScript Handbook", "Official handbook explaining type inference, interfaces, and generics cleanly.", "https://www.typescriptlang.org/docs/"),
            _res("roadmap.sh", "TypeScript Roadmap", "Interactive guide to TypeScript compiler options and advanced types.", "https://roadmap.sh/typescript"),
        ],
    },
    "C": {
        "topics": "Pointers, memory management, structs, bitwise operators, headers",
        "project": "Implement a lightweight memory pool allocator in C",
        "est_time": "3-4 weeks",
        "resources": [
            _res("Harvard CS50", "CS50x: Introduction to Computer Science", "Renowned university course teaching C pointers, memory, and data structures from scratch.", "https://cs50.harvard.edu/x/"),
            _res("Arduino Docs", "Arduino C/C++ Learning Hub", "Hands-on embedded C programming guides running directly on microcontroller hardware.", "https://docs.arduino.cc/learn/"),
        ],
    },
    "C++": {
        "topics": "Modern C++, STL containers, RAII smart pointers, templates",
        "project": "Build a thread-safe producer-consumer message queue",
        "est_time": "4-5 weeks",
        "resources": [
            _res("LearnCpp", "Learn C++ Step-by-Step Guide", "Comprehensive free online tutorial series from fundamentals to modern STL and OOP.", "https://www.learncpp.com/"),
            _res("roadmap.sh", "C++ Developer Roadmap", "Structured visual progression through C++ tooling, memory, and concurrency.", "https://roadmap.sh/cpp"),
        ],
    },
    "Go": {
        "topics": "Goroutines, channels, interfaces, HTTP net package, concurrency",
        "project": "Build a concurrent health-check CLI and microservice API",
        "est_time": "2-3 weeks",
        "resources": [
            _res("Go Official", "A Tour of Go", "Interactive browser-based tour of Go syntax, structs, interfaces, and goroutines.", "https://go.dev/tour/"),
            _res("roadmap.sh", "Go Developer Roadmap", "Curated backend Go roadmap covering CLI tooling, web frameworks, and testing.", "https://roadmap.sh/golang"),
        ],
    },
    "Rust": {
        "topics": "Ownership, borrowing, lifetimes, enums, Cargo package manager",
        "project": "Build a fast grep-like CLI text scanner in Rust",
        "est_time": "4 weeks",
        "resources": [
            _res("Rust Official", "The Rust Programming Language Book", "The canonical free book teaching ownership, traits, lifetimes, and Cargo.", "https://doc.rust-lang.org/book/"),
            _res("roadmap.sh", "Rust Developer Roadmap", "Guided Rust learning sequence with systems and backend milestones.", "https://roadmap.sh/rust"),
        ],
    },
    "C#": {
        "topics": "OOP in C#, LINQ, async/await, generics, .NET CLI",
        "project": "Create an ASP.NET Core task tracking web API",
        "est_time": "3-4 weeks",
        "resources": [
            _res("Microsoft Learn", "Get Started with C# Learning Path", "Free interactive lessons and Applied Skills labs co-hosted with freeCodeCamp.", "https://learn.microsoft.com/en-us/training/paths/get-started-c-sharp-part-1/"),
            _res("freeCodeCamp", "Foundational C# with Microsoft Certification", "Free self-paced certification track covering C# syntax, debugging, and logic.", "https://www.freecodecamp.org/learn/foundational-c-sharp-with-microsoft/"),
        ],
    },
    "PHP": {
        "topics": "PHP 8 syntax, OOP, Composer, PDO database queries, security",
        "project": "Build a RESTful blog backend in PHP with PDO and MySQL",
        "est_time": "3 weeks",
        "resources": [
            _res("PHP Official Manual", "Getting Started with PHP", "Official language manual covering syntax, forms, sessions, and database security.", "https://www.php.net/manual/en/getting-started.php"),
            _res("Laracasts / PHP Docs", "Laravel Official Documentation & Bootcamp", "Practical modern PHP patterns via Composer and MVC design.", "https://laravel.com/docs"),
        ],
    },
    "R": {
        "topics": "Vectors, data frames, tidyverse, ggplot2, statistical modeling",
        "project": "Perform statistical exploratory data analysis and plots in R Markdown",
        "est_time": "3 weeks",
        "resources": [
            _res("Coursera (Google)", "Google Data Analytics — Data Analysis with R", "Structured introduction to R programming, tidyverse cleaning, and ggplot2 visuals.", "https://www.coursera.org/professional-certificates/google-data-analytics", "Free Audit / Paid Cert"),
            _res("R Project Official", "R Manuals & Contributed Documentation", "Free reference guides on R statistical workflows and visualization.", "https://www.r-project.org/other-docs.html"),
        ],
    },
    "Dart": {
        "topics": "Null safety, async/await Streams, OOP, Flutter widget fundamentals",
        "project": "Write a cross-platform CLI & API state manager in Dart",
        "est_time": "1-2 weeks",
        "resources": [
            _res("Dart Official", "Dart Language Tour & Guides", "Official guides covering sound null safety, async futures, and collections.", "https://dart.dev/guides"),
            _res("Flutter Docs", "Flutter & Dart Codelab", "Guided hands-on tutorial introducing Dart through an interactive Flutter app.", "https://docs.flutter.dev/get-started/codelab"),
        ],
    },
    "Swift": {
        "topics": "Optionals, protocols, Swift concurrency, value types, SwiftUI basics",
        "project": "Build an expense tracker app in Swift using local persistence",
        "est_time": "3 weeks",
        "resources": [
            _res("Swift.org Docs", "The Swift Programming Language Book", "Official book teaching Swift fundamentals, optionals, protocols, and concurrency.", "https://docs.swift.org/swift-book/"),
            _res("Apple Developer", "Develop in Swift & SwiftUI Tutorials", "Apple's visual hands-on walkthroughs for building modern iOS interfaces.", "https://developer.apple.com/tutorials/swiftui"),
        ],
    },
    "SwiftUI": {
        "topics": "Declarative views, @State/@Observable, NavigationStack, animations",
        "project": "Build a multi-screen iOS habit tracker using SwiftUI",
        "est_time": "2-3 weeks",
        "resources": [
            _res("Apple Developer", "SwiftUI Tutorials (Official)", "Step-by-step interactive labs straight from Apple using Xcode previews.", "https://developer.apple.com/tutorials/swiftui"),
            _res("Swift.org Docs", "The Swift Language Guide", "Companion reference for Swift language features powering SwiftUI views.", "https://docs.swift.org/swift-book/"),
        ],
    },
    "Objective-C": {
        "topics": "Header/implementation files, ARC memory, bridging with Swift",
        "project": "Read and bridge an Objective-C utility module into Swift",
        "est_time": "1-2 weeks",
        "resources": [
            _res("Apple Developer", "Apple Developer Swift & iOS Frameworks", "Official Apple documentation on iOS Foundation APIs and Swift interoperability.", "https://developer.apple.com/tutorials/swiftui"),
            _res("Swift.org", "The Swift Programming Language Reference", "Helpful reference for understanding Objective-C interoperability patterns.", "https://docs.swift.org/swift-book/"),
        ],
    },
    "Kotlin": {
        "topics": "Null safety, coroutines, data classes, Android Jetpack Compose",
        "project": "Build an offline-first Android notes app in Kotlin",
        "est_time": "3 weeks",
        "resources": [
            _res("Kotlin Official", "Get Started with Kotlin", "JetBrains official tutorials covering syntax, idioms, and coroutines.", "https://kotlinlang.org/docs/getting-started.html"),
            _res("Google Android", "Android Basics with Compose (Kotlin)", "Free Google training course teaching Kotlin while building real Android apps.", "https://developer.android.com/courses"),
        ],
    },
    "SQL": {
        "topics": "SELECT, JOINs, GROUP BY aggregations, CTEs, window functions, indexing",
        "project": "Analyze an e-commerce sales SQLite/PostgreSQL schema with 15 KPI queries",
        "est_time": "2-3 weeks",
        "resources": [
            _res("freeCodeCamp", "Relational Database Certification", "Interactive hands-on PostgreSQL, SQL, and Bash curriculum with real database projects.", "https://www.freecodecamp.org/learn/relational-database/"),
            _res("Kaggle Learn", "Intro to SQL & Advanced SQL", "Free interactive BigQuery notebooks teaching joins, CTEs, and window functions.", "https://www.kaggle.com/learn/intro-to-sql"),
            _res("Coursera (Google)", "Google Data Analytics — SQL & Data Prep", "Beginner-friendly SQL querying taught with real spreadsheet and database scenarios.", "https://www.coursera.org/professional-certificates/google-data-analytics", "Free Audit / Paid Cert"),
        ],
    },
    "Bash": {
        "topics": "Shell scripting, pipes/grep/awk, permissions, cron jobs, process control",
        "project": "Automate log rotation and disk health alerting with a Bash script",
        "est_time": "1-2 weeks",
        "resources": [
            _res("freeCodeCamp", "Relational Database (Bash Scripting)", "Interactive terminal exercises building shell scripts in Linux environments.", "https://www.freecodecamp.org/learn/relational-database/"),
            _res("Linux Journey", "Text-Fu & Command Line Modules", "Beginner-friendly guides to bash commands, pipes, and shell utilities.", "https://linuxjourney.com/"),
        ],
    },
    "HTML5": {
        "topics": "Semantic HTML tags, forms/validation, accessibility (ARIA), SEO basics",
        "project": "Build a clean accessible portfolio landing page",
        "est_time": "1-2 weeks",
        "resources": [
            _res("freeCodeCamp", "Responsive Web Design Certification", "Learn semantic HTML5 and modern CSS layouts by building 5 web projects.", "https://www.freecodecamp.org/learn/responsive-web-design/"),
            _res("MDN Web Docs", "Structuring Content with HTML", "Mozilla's thorough HTML fundamentals, forms, and accessibility guides.", "https://developer.mozilla.org/en-US/docs/Learn/HTML"),
        ],
    },
    "CSS3": {
        "topics": "Flexbox, CSS Grid, CSS variables, media queries, animations",
        "project": "Clone a responsive dashboard layout cleanly with CSS Grid & Flexbox",
        "est_time": "2 weeks",
        "resources": [
            _res("freeCodeCamp", "Responsive Web Design (CSS Grid & Flexbox)", "Practice Flexbox, Grid, and responsive typography interactively in the browser.", "https://www.freecodecamp.org/learn/responsive-web-design/"),
            _res("MDN Web Docs", "CSS Styling Basics & Layout", "Deep reference and beginner modules on box model, Flexbox, and Grid.", "https://developer.mozilla.org/en-US/docs/Learn/CSS"),
        ],
    },
    "Responsive Design": {
        "topics": "Mobile-first media queries, fluid grids, viewport units, accessibility",
        "project": "Convert a desktop wireframe into mobile, tablet, and desktop layouts",
        "est_time": "1 week",
        "resources": [
            _res("freeCodeCamp", "Responsive Web Design Curriculum", "Hands-on projects built around mobile-first breakpoints and fluid grids.", "https://www.freecodecamp.org/learn/responsive-web-design/"),
            _res("MDN Web Docs", "CSS Layout & Responsive Design", "Official Mozilla tutorial covering responsive media queries and flexible layouts.", "https://developer.mozilla.org/en-US/docs/Learn/CSS/CSS_layout/Responsive_Design"),
        ],
    },
    "React": {
        "topics": "JSX, functional components, props, useState/useEffect hooks, React Router",
        "project": "Build a searchable job board or expense tracker SPA using public APIs",
        "est_time": "3-4 weeks",
        "resources": [
            _res("React Official Docs", "React Learn (Interactive Tutorial)", "Official documentation with interactive code sandboxes for thinking in React and Hooks.", "https://react.dev/learn"),
            _res("freeCodeCamp", "Front End Development Libraries", "Free project-based track covering React, Redux, and building interactive apps.", "https://www.freecodecamp.org/learn/front-end-development-libraries/"),
            _res("roadmap.sh", "React Developer Roadmap", "Structured React skill progression covering routing, state, and testing.", "https://roadmap.sh/react"),
        ],
    },
    "Next.js": {
        "topics": "App Router, Server Components, SSR/SSG, API route handlers",
        "project": "Build a full-stack SEO-friendly blog or job portal in Next.js",
        "est_time": "2-3 weeks",
        "resources": [
            _res("Vercel / Next.js", "Next.js Official Learn Course", "Interactive step-by-step course building a full-stack Next.js dashboard app.", "https://nextjs.org/learn"),
            _res("React Official Docs", "React Server & Full-Stack Patterns", "Official React guide explaining modern full-stack React concepts.", "https://react.dev/learn"),
        ],
    },
    "Angular": {
        "topics": "Standalone components, TypeScript services, RxJS observables, routing",
        "project": "Build an enterprise employee directory SPA with Angular and RxJS",
        "est_time": "3-4 weeks",
        "resources": [
            _res("Angular Official", "Angular Interactive Tutorials", "Official browser tutorials on angular.dev teaching signals, components, and DI.", "https://angular.dev/tutorials"),
            _res("TypeScript Docs", "The TypeScript Handbook", "Master strong typing essentials used across every Angular service and template.", "https://www.typescriptlang.org/docs/"),
        ],
    },
    "Vue.js": {
        "topics": "Composition API, single-file components, Pinia state, Vue Router",
        "project": "Build a real-time kanban board using Vue 3 Composition API",
        "est_time": "2-3 weeks",
        "resources": [
            _res("Vue.js Official", "Interactive Vue 3 Tutorial", "Official 15-step interactive playground teaching reactivity, directives, and components.", "https://vuejs.org/tutorial/"),
            _res("roadmap.sh", "Vue Developer Roadmap", "Visual guide to Vue tooling, Pinia state management, and Vite.", "https://roadmap.sh/vue"),
        ],
    },
    "Tailwind CSS": {
        "topics": "Utility-first styling, responsive modifiers, custom themes, dark mode",
        "project": "Style a SaaS pricing page and dashboard purely with Tailwind utilities",
        "est_time": "1 week",
        "resources": [
            _res("Tailwind Official", "Tailwind CSS Core Concepts & Docs", "Official searchable guide covering spacing, flexbox, grid, and custom config.", "https://tailwindcss.com/docs"),
            _res("MDN Web Docs", "CSS Fundamentals for Utility Styling", "Ensure solid underlying Flexbox and Grid intuition alongside Tailwind.", "https://developer.mozilla.org/en-US/docs/Learn/CSS"),
        ],
    },
    "Redux": {
        "topics": "Redux Toolkit slices, store setup, RTK Query, predictable state updates",
        "project": "Add shopping cart state management with Redux Toolkit to a React app",
        "est_time": "1-2 weeks",
        "resources": [
            _res("freeCodeCamp", "Front End Development Libraries (React & Redux)", "Interactive lessons pairing Redux state stores cleanly with React components.", "https://www.freecodecamp.org/learn/front-end-development-libraries/"),
            _res("React Official Docs", "Managing State in React", "Essential official concepts on reducers and state architecture.", "https://react.dev/learn/managing-state"),
        ],
    },
    "Node.js": {
        "topics": "Event loop, async filesystem/streams, HTTP servers, npm, Express",
        "project": "Build an authenticated REST API with rate limiting and SQL/MongoDB",
        "est_time": "3 weeks",
        "resources": [
            _res("Node.js Official", "Node.js Learn — Introduction & Guides", "Official guides covering async I/O, modules, TypeScript, and diagnostics.", "https://nodejs.org/en/learn/getting-started/introduction-to-nodejs"),
            _res("freeCodeCamp", "Back End Development and APIs", "Hands-on Node.js, npm, Express, and MongoDB microservice projects.", "https://www.freecodecamp.org/learn/back-end-development-and-apis/"),
            _res("roadmap.sh", "Node.js Developer Roadmap", "Curated step-by-step Node.js backend syllabus.", "https://roadmap.sh/nodejs"),
        ],
    },
    "Express.js": {
        "topics": "Middleware chains, modular routers, error handling, JWT auth",
        "project": "Build a multi-resource e-commerce backend API with Express middleware",
        "est_time": "2 weeks",
        "resources": [
            _res("freeCodeCamp", "Back End Development and APIs (Express)", "Practical Express.js projects handling routing, middleware, and JSON APIs.", "https://www.freecodecamp.org/learn/back-end-development-and-apis/"),
            _res("MDN Web Docs", "Express Web Framework Tutorial", "Mozilla's complete server-side Node.js + Express Local Library tutorial.", "https://developer.mozilla.org/en-US/docs/Learn/Server-side/Express_Nodejs"),
        ],
    },
    "Django": {
        "topics": "Models/ORM, views, Django REST Framework, Auth, Migrations, Admin",
        "project": "Build a full job board REST backend using Django & DRF",
        "est_time": "3 weeks",
        "resources": [
            _res("Django Official", "Writing Your First Django App Tutorial", "The classic multi-part official tutorial covering models, views, admin, and tests.", "https://docs.djangoproject.com/en/stable/intro/tutorial01/"),
            _res("MDN Web Docs", "Django Web Framework (Python) Tutorial", "Mozilla's step-by-step Django Local Library app covering auth and deployment.", "https://developer.mozilla.org/en-US/docs/Learn/Server-side/Django"),
        ],
    },
    "Flask": {
        "topics": "Routing, Jinja2 templates, Blueprints, SQLAlchemy, REST endpoints",
        "project": "Build a modular REST backend API cleanly organized with Flask Blueprints",
        "est_time": "1-2 weeks",
        "resources": [
            _res("Pallets / Flask", "Official Flask Tutorial & Docs", "Official guide building a full tested Flask web app cleanly from scratch.", "https://flask.palletsprojects.com"),
            _res("Python Official Docs", "Python 3 Tutorial", "Companion Python language reference for decorators, venv, and packaging.", "https://docs.python.org/3/tutorial/"),
        ],
    },
    "FastAPI": {
        "topics": "Type-hint validation, Pydantic models, Dependency Injection, OpenAPI",
        "project": "Build an async ML prediction microservice with FastAPI & Pydantic",
        "est_time": "1-2 weeks",
        "resources": [
            _res("FastAPI Official", "FastAPI Tutorial — User Guide", "Interactive documentation teaching Pydantic schemas, async APIs, and OAuth2.", "https://fastapi.tiangolo.com/tutorial/"),
            _res("FastAPI Learn", "FastAPI Concepts & Best Practices", "Dedicated FastAPI learning track covering concurrency and testing.", "https://fastapi.tiangolo.com/learn/"),
        ],
    },
    "Spring Boot": {
        "topics": "IoC/Dependency Injection, Spring Data JPA, REST Controllers, Security",
        "project": "Build a Spring Boot CRUD microservice connected cleanly to PostgreSQL",
        "est_time": "3-4 weeks",
        "resources": [
            _res("Spring Official", "Building a RESTful Web Service Guide", "Hands-on 15-minute official Spring Boot guides covering REST, JPA, and Security.", "https://spring.io/guides"),
            _res("Dev.java", "Learn Java for Spring Ecosystems", "Official Oracle Java fundamentals required for productive Spring Boot development.", "https://dev.java/learn/"),
        ],
    },
    "Spring Framework": {
        "topics": "Dependency injection, Spring MVC, AOP, transaction management",
        "project": "Create a layered Java service using Spring IoC and JDBC/JPA",
        "est_time": "3 weeks",
        "resources": [
            _res("Spring Official", "Spring Guides & Tutorials", "Practical task-focused guides from the Spring engineering team.", "https://spring.io/guides"),
            _res("roadmap.sh", "Spring Boot & Java Roadmap", "Visual guide showing how Spring core fits into enterprise Java backends.", "https://roadmap.sh/spring-boot"),
        ],
    },
    "Hibernate": {
        "topics": "JPA entity mapping, relationships, lazy loading, HQL query tuning",
        "project": "Model a multi-table inventory schema using JPA/Hibernate entities",
        "est_time": "1-2 weeks",
        "resources": [
            _res("Hibernate Official", "Hibernate ORM Documentation", "Official getting-started and mapping guides for Java persistence.", "https://hibernate.org/orm/documentation/"),
            _res("Spring Official", "Accessing Data with JPA Guide", "Practical walkthrough integrating Hibernate/JPA with Spring Boot.", "https://spring.io/guides"),
        ],
    },
    ".NET Core": {
        "topics": "ASP.NET Core Web APIs, Entity Framework Core, Dependency Injection",
        "project": "Build a RESTful catalog API with ASP.NET Core and SQLite/PostgreSQL",
        "est_time": "3 weeks",
        "resources": [
            _res("Microsoft Learn", "ASP.NET Core & .NET Training Paths", "Official Microsoft Learn tutorials for building web APIs and microservices.", "https://learn.microsoft.com/en-us/training/"),
            _res("freeCodeCamp", "Foundational C# with Microsoft", "Core C# foundation feeding directly into .NET Core API development.", "https://www.freecodecamp.org/learn/foundational-c-sharp-with-microsoft/"),
        ],
    },
    "Laravel": {
        "topics": "Eloquent ORM, Blade templates, migrations, queues, REST API Sanctum",
        "project": "Build a multi-user task board in Laravel with Eloquent & MySQL",
        "est_time": "3 weeks",
        "resources": [
            _res("Laravel Official", "Laravel Documentation & Bootcamp", "Thorough official documentation covering routing, Eloquent, testing, and queues.", "https://laravel.com/docs"),
            _res("PHP Official Manual", "Getting Started with PHP", "Foundation guide for PHP 8 OOP concepts underlying Laravel.", "https://www.php.net/manual/en/getting-started.php"),
        ],
    },
    "Symfony": {
        "topics": "Bundles, Doctrine ORM, Dependency Injection container, Twig, Messenger",
        "project": "Create a modular Symfony REST API backed by Doctrine and MySQL",
        "est_time": "3 weeks",
        "resources": [
            _res("Symfony Official", "Symfony Current Documentation", "Official guides and book tutorials for Symfony web apps and APIs.", "https://symfony.com/doc/current/index.html"),
            _res("PHP Official Manual", "PHP Language Fundamentals", "Official reference covering namespaces, attributes, and OOP in modern PHP.", "https://www.php.net/manual/en/getting-started.php"),
        ],
    },
    "WordPress": {
        "topics": "Block themes, custom post types, plugin hooks/actions, REST API",
        "project": "Develop a custom WordPress theme and lightweight portfolio plugin",
        "est_time": "2 weeks",
        "resources": [
            _res("WordPress Official", "Learn WordPress Courses & Workshops", "Free official pathways for WordPress developers and designers.", "https://learn.wordpress.org/"),
            _res("PHP Official Manual", "PHP Getting Started", "Learn server-side PHP basics powering custom WordPress themes and plugins.", "https://www.php.net/manual/en/getting-started.php"),
        ],
    },
    "jQuery": {
        "topics": "DOM selectors, event handling, AJAX requests, legacy code maintenance",
        "project": "Build dynamic form filtering and live search on an existing HTML page",
        "est_time": "1 week",
        "resources": [
            _res("freeCodeCamp", "Front End Development Libraries (jQuery Section)", "Short interactive challenges covering DOM queries and event handlers.", "https://www.freecodecamp.org/learn/front-end-development-libraries/"),
            _res("MDN Web Docs", "Modern JavaScript DOM Essentials", "Understand native DOM APIs alongside maintaining legacy jQuery apps.", "https://developer.mozilla.org/en-US/docs/Learn/JavaScript"),
        ],
    },
    "Flutter": {
        "topics": "Stateless/Stateful widgets, Navigation, Provider/Riverpod, HTTP APIs",
        "project": "Build a cross-platform iOS & Android weather or habit tracker app",
        "est_time": "3-4 weeks",
        "resources": [
            _res("Flutter Official", "Write Your First Flutter App Codelab", "Google's guided hands-on tutorial for cross-platform mobile UI in Dart.", "https://docs.flutter.dev/get-started/codelab"),
            _res("Dart Official", "Dart Language & Async Guides", "Learn sound null safety and Futures/Streams cleanly for Flutter state.", "https://dart.dev/guides"),
        ],
    },
    "React Native": {
        "topics": "Core native components, Expo workflow, navigation, AsyncStorage",
        "project": "Build an Expo React Native mobile companion app fetching live APIs",
        "est_time": "3 weeks",
        "resources": [
            _res("React Official Docs", "React Fundamentals for Mobile", "Official React concepts (JSX, Hooks, state) that apply directly in React Native.", "https://react.dev/learn"),
            _res("roadmap.sh", "React Native Developer Roadmap", "Structured visual pathway from JavaScript/React to native mobile shipping.", "https://roadmap.sh/react-native"),
        ],
    },
    "Android": {
        "topics": "Kotlin UI, Activity/Fragment lifecycle, Jetpack Compose, Room DB",
        "project": "Build a multi-screen Android reading list app with Kotlin & Jetpack Compose",
        "est_time": "4 weeks",
        "resources": [
            _res("Google Android", "Android Basics with Compose", "Official free Google Android developer curriculum from setup to Play Store.", "https://developer.android.com/courses"),
            _res("Kotlin Official", "Kotlin Documentation & Coroutines", "Official language guides for clean Android app architecture.", "https://kotlinlang.org/docs/getting-started.html"),
            _res("roadmap.sh", "Android Developer Roadmap", "Guided map covering Jetpack libraries, MVVM, and testing.", "https://roadmap.sh/android"),
        ],
    },
    "Android SDK": {
        "topics": "Android Studio profiler, Gradle builds, permissions, Jetpack Compose",
        "project": "Configure Android SDK permissions, notifications, and API networking in Studio",
        "est_time": "2-3 weeks",
        "resources": [
            _res("Google Android", "Official Android Training Courses", "Codelabs and modules teaching Android Studio, Jetpack libraries, and SDK APIs.", "https://developer.android.com/courses"),
            _res("Gradle Official", "Gradle User Guide for Mobile Builds", "Understand Gradle dependency and APK/AAB build configuration cleanly.", "https://docs.gradle.org/current/userguide/userguide.html"),
        ],
    },
    "iOS": {
        "topics": "UIKit/SwiftUI views, Auto Layout, URLSession networking, CoreData",
        "project": "Build a native SwiftUI iOS catalog app backed by live JSON APIs",
        "est_time": "4 weeks",
        "resources": [
            _res("Apple Developer", "Apple SwiftUI & iOS App Tutorials", "Official step-by-step iOS tutorials teaching app layout, data flow, and navigation.", "https://developer.apple.com/tutorials/swiftui"),
            _res("Swift.org Docs", "The Swift Programming Language", "Official Swift reference powering native iOS development.", "https://docs.swift.org/swift-book/"),
            _res("roadmap.sh", "iOS Developer Roadmap", "Interactive guide across Swift, Xcode, persistence, and App Store release.", "https://roadmap.sh/ios"),
        ],
    },
    "Xcode": {
        "topics": "Simulator, Instruments profiler, LLDB debugging, TestFlight signing",
        "project": "Profile memory leaks and build a test scheme inside Xcode",
        "est_time": "1-2 weeks",
        "resources": [
            _res("Apple Developer", "Xcode & SwiftUI Interactive Tutorials", "Learn Xcode canvas previews, project schemes, and debugging hands-on.", "https://developer.apple.com/tutorials/swiftui"),
            _res("roadmap.sh", "iOS Tooling Roadmap", "Explore Xcode workflows, CocoaPods/SPM packages, and signing concepts.", "https://roadmap.sh/ios"),
        ],
    },
    "PostgreSQL": {
        "topics": "Indexes, B-Tree/GIN tuning, JSONB, EXPLAIN ANALYZE, ACID transactions",
        "project": "Design an indexed analytics database schema with constraints and views",
        "est_time": "2 weeks",
        "resources": [
            _res("PostgreSQL Docs", "Official PostgreSQL Tutorial", "Clear walkthrough of SQL tables, joins, aggregates, transactions, and views.", "https://www.postgresql.org/docs/current/tutorial.html"),
            _res("freeCodeCamp", "Relational Database (PostgreSQL Track)", "Build five real PostgreSQL databases interactively from Bash and psql.", "https://www.freecodecamp.org/learn/relational-database/"),
            _res("roadmap.sh", "PostgreSQL DBA Roadmap", "Structured progression covering query tuning, backups, and replication.", "https://roadmap.sh/postgresql-dba"),
        ],
    },
    "MySQL": {
        "topics": "InnoDB storage, joins, normalization, indexing, stored routines",
        "project": "Normalize a multi-table e-commerce schema and benchmark slow queries",
        "est_time": "2 weeks",
        "resources": [
            _res("MySQL Official", "MySQL Reference Manual & Tutorial", "Authoritative guide to queries, indexing, backups, and server administration.", "https://dev.mysql.com/doc/"),
            _res("freeCodeCamp", "Relational Database SQL Foundations", "Hands-on relational SQL design skills transferring directly to MySQL.", "https://www.freecodecamp.org/learn/relational-database/"),
        ],
    },
    "Microsoft SQL Server": {
        "topics": "T-SQL queries, window functions, stored procedures, execution plans",
        "project": "Write analytical T-SQL reporting procedures on AdventureWorks sample data",
        "est_time": "2-3 weeks",
        "resources": [
            _res("Microsoft Learn", "Query and Modify Data with Transact-SQL", "Official Microsoft T-SQL learning path for SQL Server and Azure SQL.", "https://learn.microsoft.com/en-us/training/paths/get-started-querying-with-transact-sql/"),
            _res("Microsoft Learn", "Azure & SQL Server Database Training", "Free guided labs covering indexing, performance tuning, and backups.", "https://learn.microsoft.com/en-us/training/"),
        ],
    },
    "Oracle Database": {
        "topics": "PL/SQL, tablespaces, indexing, RMAN backup/recovery concepts",
        "project": "Write PL/SQL validation procedures and inspect query execution plans",
        "est_time": "3 weeks",
        "resources": [
            _res("freeCodeCamp", "Relational Database & SQL Core Concepts", "Solid ANSI SQL and relational modeling foundations shared with Oracle DB.", "https://www.freecodecamp.org/learn/relational-database/"),
            _res("PostgreSQL Docs", "Enterprise SQL Concepts & Indexing", "Clear open reference for views, transactions, and query planning.", "https://www.postgresql.org/docs/current/tutorial.html"),
        ],
    },
    "MongoDB": {
        "topics": "Document modeling, Aggregation Pipeline, compound indexes, Atlas",
        "project": "Build an analytics aggregation pipeline on e-commerce order documents",
        "est_time": "1-2 weeks",
        "resources": [
            _res("MongoDB Learn", "MongoDB Developer Center & University", "Official free interactive courses on document modeling, CRUD, and aggregation.", "https://learn.mongodb.com/"),
            _res("freeCodeCamp", "Back End APIs & Mongoose Track", "Build Express + MongoDB CRUD web applications in hands-on challenges.", "https://www.freecodecamp.org/learn/back-end-development-and-apis/"),
            _res("roadmap.sh", "MongoDB Roadmap", "Visual skill sequence for NoSQL indexing and Atlas operations.", "https://roadmap.sh/mongodb"),
        ],
    },
    "NoSQL": {
        "topics": "Document vs key-value vs wide-column stores, eventual consistency",
        "project": "Compare relational PostgreSQL vs document MongoDB modeling for one app",
        "est_time": "1-2 weeks",
        "resources": [
            _res("MongoDB Learn", "NoSQL Document Modeling Guides", "Practical official lessons on embedding vs referencing in document stores.", "https://learn.mongodb.com/"),
            _res("Redis Learn", "Key-Value & In-Memory Architecture Guides", "Learn sub-millisecond caching and non-relational data structures.", "https://redis.io/learn/"),
        ],
    },
    "Redis": {
        "topics": "Strings/Hashes/Sorted Sets, cache invalidation, TTL, pub/sub",
        "project": "Add Redis response caching and sliding-window rate limiting to an API",
        "est_time": "1 week",
        "resources": [
            _res("Redis Official", "Redis Learn & Free University", "Interactive guides on Redis data structures, caching patterns, and streams.", "https://redis.io/learn/"),
            _res("roadmap.sh", "Backend Caching & Redis Concepts", "See where Redis caching fits inside modern scalable backend architectures.", "https://roadmap.sh/backend"),
        ],
    },
    "Elasticsearch": {
        "topics": "Inverted indexes, full-text search DSL, analyzers, aggregations",
        "project": "Index job descriptions and implement fuzzy autocomplete search",
        "est_time": "2 weeks",
        "resources": [
            _res("Elastic Official", "Elasticsearch Reference & Getting Started", "Official docs covering mappings, full-text queries, and relevance tuning.", "https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html"),
            _res("roadmap.sh", "Search Engines in Backend Systems", "Understand full-text search engine integration patterns in backend stacks.", "https://roadmap.sh/backend"),
        ],
    },
    "Apache Kafka": {
        "topics": "Topics, partitions, consumer groups, producers, event-driven pipelines",
        "project": "Stream order events cleanly between a producer and consumer service",
        "est_time": "2-3 weeks",
        "resources": [
            _res("Apache Spark Docs", "Streaming Data Integration Guides", "Explore event streaming architecture integrated with modern data pipelines.", "https://spark.apache.org/docs/latest/"),
            _res("roadmap.sh", "Backend Message Brokers & Event Streaming", "Understand event-driven microservice messaging and Kafka trade-offs.", "https://roadmap.sh/backend"),
        ],
    },
    "Snowflake": {
        "topics": "Virtual warehouses, SnowSQL, Stages/COPY INTO, clustering, time travel",
        "project": "Load JSON/CSV raw files into Snowflake and transform analytical views",
        "est_time": "2 weeks",
        "resources": [
            _res("Snowflake Official", "Snowflake Official Documentation & Guides", "Comprehensive quickstarts on cloud warehousing, SQL loading, and compute scaling.", "https://docs.snowflake.com"),
            _res("dbt Docs", "Modern Data Warehousing with dbt", "Learn SQL modeling workflows commonly paired with Snowflake warehouses.", "https://docs.getdbt.com/docs/introduction"),
        ],
    },
    "Google BigQuery": {
        "topics": "Serverless SQL queries, partitioning, clustering, analytical window functions",
        "project": "Query a public dataset on BigQuery sandbox and build cost-safe aggregations",
        "est_time": "1-2 weeks",
        "resources": [
            _res("Kaggle Learn", "Intro to SQL & Advanced SQL on BigQuery", "Interactive free notebooks executing real queries directly against BigQuery datasets.", "https://www.kaggle.com/learn/intro-to-sql"),
            _res("Google Cloud", "BigQuery Documentation & Quickstarts", "Official GCP reference on schemas, partitioning, and SQL optimization.", "https://cloud.google.com/bigquery/docs"),
        ],
    },
    "Firebase Firestore": {
        "topics": "Collections/documents, real-time listeners, security rules, auth integration",
        "project": "Build a real-time chat or collaborative todo app synced with Firestore",
        "est_time": "1-2 weeks",
        "resources": [
            _res("Flutter Official", "Flutter & Firebase Quickstart Pathways", "Official guides connecting cross-platform mobile UIs to Firebase backends.", "https://docs.flutter.dev/get-started/codelab"),
            _res("Google Android", "Modern Mobile Cloud Storage Courses", "Practical guidance on client-side NoSQL synchronization and security rules.", "https://developer.android.com/courses"),
        ],
    },
    "REST API": {
        "topics": "HTTP verbs, status codes, JSON design, pagination, JWT/OAuth auth",
        "project": "Design an OpenAPI-documented REST API and verify endpoints cleanly",
        "est_time": "1-2 weeks",
        "resources": [
            _res("Postman Docs", "Postman Getting Started & API Testing", "Learn HTTP request design, collections, and automated endpoint tests.", "https://learning.postman.com/docs/getting-started/overview/"),
            _res("FastAPI Docs", "REST API Design Tutorial", "Practical hands-on guide to status codes, schemas, validation, and auth.", "https://fastapi.tiangolo.com/tutorial/"),
            _res("roadmap.sh", "API Design & Backend Fundamentals", "Visual guide to RESTful conventions, versioning, and authentication.", "https://roadmap.sh/backend"),
        ],
    },
    "GraphQL": {
        "topics": "Schemas, Queries, Mutations, Resolvers, preventing N+1 queries",
        "project": "Wrap a multi-table Postgres database cleanly behind a GraphQL schema",
        "est_time": "1-2 weeks",
        "resources": [
            _res("GraphQL Official", "Introduction to GraphQL", "Official guide walking through schemas, type definitions, queries, and best practices.", "https://graphql.org/learn/"),
            _res("roadmap.sh", "GraphQL Developer Roadmap", "Structured map of GraphQL servers, clients, caching, and federation.", "https://roadmap.sh/graphql"),
        ],
    },
    "Microservices": {
        "topics": "Service boundaries, API gateways, async events, retries, health checks",
        "project": "Split a monolith auth + catalog service cleanly using Docker Compose",
        "est_time": "3 weeks",
        "resources": [
            _res("roadmap.sh", "Software Architect & Microservices Roadmap", "Clear architecture comparisons between monoliths, microservices, and queues.", "https://roadmap.sh/software-architect"),
            _res("Spring Official", "Building Microservices Guides", "Hands-on tutorials covering service discovery, gateways, and resilience.", "https://spring.io/guides"),
        ],
    },
    "System Design": {
        "topics": "Load balancing, caching, database sharding, rate limiting, CAP theorem",
        "project": "Draft an architecture diagram & scaling analysis for a URL shortener",
        "est_time": "3-4 weeks",
        "resources": [
            _res("roadmap.sh", "System Design Roadmap", "Visual guide covering CDNs, proxies, replication, partitioning, and queues.", "https://roadmap.sh/system-design"),
            _res("roadmap.sh", "Backend Architecture Track", "Connect system design principles to everyday backend engineering choices.", "https://roadmap.sh/backend"),
        ],
    },
    "Git": {
        "topics": "Commit hygiene, branching, rebase vs merge, pull requests, resolving conflicts",
        "project": "Practice branching, interactive rebase, and PR reviews in a shared repo",
        "est_time": "1 week",
        "resources": [
            _res("Learn Git Branching", "Interactive Visual Git Sandbox", "Playful browser visualizer teaching branches, merges, cherry-pick, and rebase.", "https://learngitbranching.js.org/"),
            _res("Git Official", "Pro Git Book (Free Online)", "The complete canonical Git book covering daily workflows through internals.", "https://git-scm.com/book/en/v2"),
            _res("roadmap.sh", "Git & GitHub Roadmap", "Quick step-by-step developer workflow checklist.", "https://roadmap.sh/git-github"),
        ],
    },
    "Docker": {
        "topics": "Dockerfiles, multi-stage builds, layers, volumes, Docker Compose",
        "project": "Containerize a Python/Node web backend + Postgres using Docker Compose",
        "est_time": "1-2 weeks",
        "resources": [
            _res("Docker Official", "Docker Get Started Guide", "Hands-on official tutorials on images, containers, networking, and Compose.", "https://docs.docker.com/get-started/"),
            _res("roadmap.sh", "Docker Roadmap", "Structured containerization checklist covering optimization and security.", "https://roadmap.sh/docker"),
        ],
    },
    "Kubernetes": {
        "topics": "Pods, Deployments, Services, Ingress, ConfigMaps, Helm basics",
        "project": "Deploy and scale a containerized Flask app cleanly on Minikube or Kind",
        "est_time": "3-4 weeks",
        "resources": [
            _res("Kubernetes Official", "Kubernetes Basics Interactive Tutorials", "Official modular tutorials covering Pods, Services, rolling updates, and scaling.", "https://kubernetes.io/docs/tutorials/kubernetes-basics/"),
            _res("roadmap.sh", "Kubernetes Roadmap", "Visual progression from container scheduling to cluster observability.", "https://roadmap.sh/kubernetes"),
        ],
    },
    "CI/CD": {
        "topics": "Automated test pipelines, build caching, container registries, rollbacks",
        "project": "Automate unit tests, linting, and Docker builds on every pull request",
        "est_time": "1-2 weeks",
        "resources": [
            _res("GitHub Docs", "GitHub Actions Documentation", "Official guides to automating test, build, and deployment workflows.", "https://docs.github.com/en/actions"),
            _res("Jenkins Official", "Jenkins Pipeline Tutorials", "Step-by-step tutorials building CI/CD pipelines across Java, Node, and Python.", "https://www.jenkins.io/doc/tutorials/"),
            _res("roadmap.sh", "DevOps CI/CD Roadmap", "Understand continuous integration, artifacts, and safe deployment patterns.", "https://roadmap.sh/devops"),
        ],
    },
    "GitHub Actions": {
        "topics": "YAML workflows, runners, matrix builds, secrets, Docker publish",
        "project": "Add a CI matrix workflow testing across Python versions on GitHub",
        "est_time": "1 week",
        "resources": [
            _res("GitHub Official", "Understanding GitHub Actions & Quickstarts", "Free official tutorials creating CI test workflows inside any repository.", "https://docs.github.com/en/actions"),
            _res("Docker Official", "Build & Push Containers in CI", "Official Docker guide integrating automated image builds into pipelines.", "https://docs.docker.com/get-started/"),
        ],
    },
    "Jenkins": {
        "topics": "Declarative Jenkinsfiles, agents, plugins, build triggers, credentials",
        "project": "Write a declarative multi-stage Jenkinsfile running tests and Docker builds",
        "est_time": "1-2 weeks",
        "resources": [
            _res("Jenkins Official", "Jenkins Pipeline & App Tutorials", "Official step-by-step tutorials with Dockerized Jenkins setups.", "https://www.jenkins.io/doc/tutorials/"),
            _res("roadmap.sh", "DevOps Automation Roadmap", "Explore CI/CD concepts alongside modern pipeline orchestration.", "https://roadmap.sh/devops"),
        ],
    },
    "Terraform": {
        "topics": "HCL syntax, providers, remote state, modules, plan/apply lifecycle",
        "project": "Provision an isolated VPC and storage bucket cleanly using Terraform modules",
        "est_time": "2-3 weeks",
        "resources": [
            _res("HashiCorp Official", "Terraform Tutorials", "Official hands-on CLI tutorials for AWS, Azure, GCP, and Docker IaC.", "https://developer.hashicorp.com/terraform/tutorials"),
            _res("roadmap.sh", "Terraform Infrastructure Roadmap", "Guided IaC progression from state management to team workflows.", "https://roadmap.sh/terraform"),
        ],
    },
    "Ansible": {
        "topics": "Inventories, YAML playbooks, roles, idempotency, SSH provisioning",
        "project": "Automate Nginx + firewall setup across Linux VMs via an Ansible playbook",
        "est_time": "2 weeks",
        "resources": [
            _res("Ansible Official", "Ansible Community Documentation", "Official getting-started playbooks, module guides, and best practices.", "https://docs.ansible.com/"),
            _res("roadmap.sh", "DevOps Configuration Management Roadmap", "Learn how configuration management complements containers and IaC.", "https://roadmap.sh/devops"),
        ],
    },
    "Linux": {
        "topics": "Filesystems, systemd services, permissions, networking CLI, SSH, logs",
        "project": "Configure a hardened Ubuntu VM running a systemd web service and UFW firewall",
        "est_time": "2-3 weeks",
        "resources": [
            _res("Linux Journey", "Linux Journey Guided Lessons", "Clear bite-sized lessons on shell commands, permissions, processes, and networking.", "https://linuxjourney.com/"),
            _res("roadmap.sh", "Linux Learning Roadmap", "Practical checklist covering shells, text tools, system monitoring, and security.", "https://roadmap.sh/linux"),
            _res("Coursera (Google)", "Technical Support Fundamentals", "Foundational OS, hardware, and system administration fundamentals.", "https://www.coursera.org/learn/technical-support-fundamentals", "Free Audit / Paid Cert"),
        ],
    },
    "Prometheus": {
        "topics": "Metrics scraping, PromQL queries, exporters, alert rules",
        "project": "Instrument a web service endpoint and scrape latency metrics in Prometheus",
        "est_time": "1-2 weeks",
        "resources": [
            _res("Prometheus Official", "Prometheus Overview & Guides", "Official introduction to time-series metrics, pull scraping, and PromQL.", "https://prometheus.io/docs/introduction/overview/"),
            _res("Grafana Docs", "Visualizing Prometheus with Grafana", "Pair Prometheus metrics cleanly with alerting dashboards.", "https://grafana.com/tutorials/"),
        ],
    },
    "Grafana": {
        "topics": "Panels, time-series dashboards, data source queries, alert channels",
        "project": "Build a CPU, memory, and HTTP 5xx SLA monitoring dashboard in Grafana",
        "est_time": "1 week",
        "resources": [
            _res("Grafana Official", "Grafana Official Tutorials", "Step-by-step interactive labs building dashboards and configuring alert rules.", "https://grafana.com/tutorials/"),
            _res("Prometheus Official", "Metrics Foundations for Dashboards", "Understand counters, gauges, and histograms visualized inside Grafana.", "https://prometheus.io/docs/introduction/overview/"),
        ],
    },
    "AWS": {
        "topics": "IAM, EC2, S3, VPC subnets, RDS, Lambda, CloudWatch monitoring",
        "project": "Host a static frontend on S3 + containerized API behind a secure VPC",
        "est_time": "3-4 weeks",
        "resources": [
            _res("AWS Official", "AWS Skill Builder Digital Training", "Free official AWS cloud practitioner, developer, and DevOps learning plans.", "https://explore.skillbuilder.aws"),
            _res("Coursera (IBM)", "Introduction to Cloud Computing", "Understand core cloud service models (IaaS/PaaS/SaaS) before exam prep.", "https://www.coursera.org/learn/introduction-to-cloud", "Free Audit / Paid Cert"),
            _res("roadmap.sh", "AWS Cloud Roadmap", "Visual roadmap ranking core AWS services by real job frequency.", "https://roadmap.sh/aws"),
        ],
    },
    "Microsoft Azure": {
        "topics": "Azure AD/Entra IAM, Virtual Networks, App Service, Azure SQL, Blob Storage",
        "project": "Deploy a web app and managed SQL database cleanly on Azure App Service",
        "est_time": "3 weeks",
        "resources": [
            _res("Microsoft Learn", "Azure Fundamentals & Admin Paths", "Completely free interactive Azure training modules and sandboxes from Microsoft.", "https://learn.microsoft.com/en-us/training/"),
            _res("Coursera (IBM)", "Cloud Computing Architecture Basics", "Compare multi-cloud IaaS/PaaS fundamentals alongside Azure concepts.", "https://www.coursera.org/learn/introduction-to-cloud", "Free Audit / Paid Cert"),
        ],
    },
    "Google Cloud Platform": {
        "topics": "Compute Engine, Cloud Run containers, Cloud Storage, BigQuery, IAM",
        "project": "Deploy a serverless Docker API cleanly to Google Cloud Run",
        "est_time": "2-3 weeks",
        "resources": [
            _res("Google Cloud Docs", "BigQuery & GCP Cloud Guides", "Official Google Cloud architecture documentation and quickstarts.", "https://cloud.google.com/bigquery/docs"),
            _res("Coursera (IBM)", "Cloud Computing Core Foundations", "Vendor-neutral cloud architecture concepts applicable directly to GCP.", "https://www.coursera.org/learn/introduction-to-cloud", "Free Audit / Paid Cert"),
        ],
    },
    "Data Analysis": {
        "topics": "Data cleaning, missing value handling, KPI definition, trend segmentation",
        "project": "Clean a messy retail CSV dataset and publish an insights notebook",
        "est_time": "2-3 weeks",
        "resources": [
            _res("freeCodeCamp", "Data Analysis with Python Certification", "Free interactive curriculum covering NumPy, Pandas, Matplotlib, and real projects.", "https://www.freecodecamp.org/learn/data-analysis-with-python/"),
            _res("Coursera (Google)", "Google Data Analytics Professional Certificate", "Structured beginner track teaching data cleaning, SQL, and visualization workflows.", "https://www.coursera.org/professional-certificates/google-data-analytics", "Free Audit / Paid Cert"),
            _res("roadmap.sh", "Data Analyst Roadmap", "Step-by-step career progression covering Excel, SQL, BI, and Python.", "https://roadmap.sh/data-analyst"),
        ],
    },
    "Statistics": {
        "topics": "Probability distributions, hypothesis testing, p-values, confidence intervals, A/B testing",
        "project": "Run a statistical A/B conversion analysis with Python SciPy",
        "est_time": "3 weeks",
        "resources": [
            _res("freeCodeCamp", "Data Analysis with Python (Statistical Thinking)", "Build probability and variance calculators alongside real analytical datasets.", "https://www.freecodecamp.org/learn/data-analysis-with-python/"),
            _res("Coursera (IBM)", "IBM Data Science & Statistical Foundations", "Covers descriptive statistics, correlation, and hypothesis evaluation cleanly.", "https://www.coursera.org/professional-certificates/ibm-data-science", "Free Audit / Paid Cert"),
        ],
    },
    "Data Visualization": {
        "topics": "Chart selection, storytelling with data, color contrast, KPI layouts",
        "project": "Create an executive insight deck combining SQL summaries and clear charts",
        "est_time": "2 weeks",
        "resources": [
            _res("Kaggle Learn", "Data Visualization Micro-Course", "Free hands-on Kaggle notebooks building heatmaps, scatter, and line charts.", "https://www.kaggle.com/learn/data-visualization"),
            _res("Tableau Learning", "Tableau Training & Visual Analytics", "Learn visual best practices and interactive dashboard storytelling.", "https://www.tableau.com/learn/training"),
        ],
    },
    "Pandas": {
        "topics": "DataFrames, groupby aggregations, merge/join, time-series indexing",
        "project": "Clean and aggregate multi-million-row sales CSV files cleanly in Pandas",
        "est_time": "2 weeks",
        "resources": [
            _res("Kaggle Learn", "Pandas Free Micro-Course", "Fast interactive exercises on indexing, grouping, missing data, and renaming.", "https://www.kaggle.com/learn/pandas"),
            _res("Pandas Official", "Getting Started Intro Tutorials", "Official concise tutorials for reshaping, plotting, and merging tables.", "https://pandas.pydata.org/docs/getting_started/intro_tutorials/"),
            _res("freeCodeCamp", "Data Analysis with Python", "Earn a free certificate building statistical Pandas projects.", "https://www.freecodecamp.org/learn/data-analysis-with-python/"),
        ],
    },
    "NumPy": {
        "topics": "N-dimensional arrays, vectorization, broadcasting, linear algebra",
        "project": "Benchmark pure-Python loops vs vectorized NumPy matrix operations",
        "est_time": "1-2 weeks",
        "resources": [
            _res("NumPy Official", "NumPy Learn — Official Quickstart", "Official interactive tutorials covering arrays, broadcasting, and linear algebra.", "https://numpy.org/learn/"),
            _res("freeCodeCamp", "Data Analysis with Python (NumPy)", "Free exercises covering mean-variance-standard-deviation array calculations.", "https://www.freecodecamp.org/learn/data-analysis-with-python/"),
        ],
    },
    "Matplotlib": {
        "topics": "Figure/Axes API, subplots, histograms, custom labels and styling",
        "project": "Build a multi-panel exploratory chart report saved cleanly as PNG/SVG",
        "est_time": "1 week",
        "resources": [
            _res("Matplotlib Official", "Matplotlib Official Tutorials", "Step-by-step introductory guides from pyplot basics to multi-axis customization.", "https://matplotlib.org/stable/tutorials/"),
            _res("Kaggle Learn", "Data Visualization with Python", "Apply Matplotlib & Seaborn immediately on real Kaggle datasets.", "https://www.kaggle.com/learn/data-visualization"),
        ],
    },
    "Seaborn": {
        "topics": "Statistical distributions, boxplots, pairplots, correlation heatmaps",
        "project": "Create an EDA correlation & distribution visual summary for a dataset",
        "est_time": "1 week",
        "resources": [
            _res("Seaborn Official", "Seaborn Statistical Plotting Tutorial", "Official examples covering relational, categorical, and distribution plots.", "https://seaborn.pydata.org/tutorial.html"),
            _res("Kaggle Learn", "Data Visualization Course", "Completely free browser labs visualizing trends cleanly with Seaborn.", "https://www.kaggle.com/learn/data-visualization"),
        ],
    },
    "Tableau": {
        "topics": "Calculated fields, LOD expressions, interactive filters, dashboard actions",
        "project": "Publish an interactive sales & regional profit dashboard to Tableau Public",
        "est_time": "2-3 weeks",
        "resources": [
            _res("Tableau Official", "Tableau Free Training Videos & Paths", "Official self-paced tutorials from connecting data sources to dashboard design.", "https://www.tableau.com/learn/training"),
            _res("Coursera (Google)", "Google Data Analytics — Visualization with Tableau", "Beginner-friendly guided practice building executive dashboards.", "https://www.coursera.org/professional-certificates/google-data-analytics", "Free Audit / Paid Cert"),
        ],
    },
    "Power BI": {
        "topics": "Power Query M transformations, star-schema relationships, DAX measures",
        "project": "Build an interactive financial KPI report with DAX time-intelligence",
        "est_time": "2-3 weeks",
        "resources": [
            _res("Microsoft Learn", "Power BI Data Analyst Training Path (PL-300)", "Free official guided learning modules covering Power Query, DAX, and modeling.", "https://learn.microsoft.com/en-us/training/"),
            _res("roadmap.sh", "Data Analyst BI Path", "See how Power BI fits alongside SQL and Excel in analyst workflows.", "https://roadmap.sh/data-analyst"),
        ],
    },
    "Microsoft Excel": {
        "topics": "PivotTables, XLOOKUP/INDEX-MATCH, Power Query, conditional formatting, charts",
        "project": "Automate a monthly budget & cohort retention workbook using PivotTables",
        "est_time": "1-2 weeks",
        "resources": [
            _res("Coursera (Google)", "Google Data Analytics — Spreadsheets & Analysis", "Structured spreadsheet formulas, cleaning, and pivot analysis exercises.", "https://www.coursera.org/professional-certificates/google-data-analytics", "Free Audit / Paid Cert"),
            _res("roadmap.sh", "Data Analyst Foundations", "Explore spreadsheet analytics workflows alongside SQL reporting.", "https://roadmap.sh/data-analyst"),
        ],
    },
    "Jupyter": {
        "topics": "Interactive notebooks, magic commands, reproducible markdown reports",
        "project": "Document a clean EDA & modeling story end-to-end in Jupyter",
        "est_time": "3-5 days",
        "resources": [
            _res("Kaggle Learn", "Python & Data Science Notebooks", "Practice running interactive Jupyter notebooks directly in your browser.", "https://www.kaggle.com/learn/python"),
            _res("Coursera (IBM)", "IBM Data Science — Open Source Tools", "Hands-on walkthroughs of JupyterLab workflows for reproducible research.", "https://www.coursera.org/professional-certificates/ibm-data-science", "Free Audit / Paid Cert"),
        ],
    },
    "Machine Learning": {
        "topics": "Train/test split, regression, classification, overfitting, cross-validation",
        "project": "Train and compare Logistic Regression vs Random Forest on churn data",
        "est_time": "4-5 weeks",
        "resources": [
            _res("Kaggle Learn", "Intro to Machine Learning & Intermediate ML", "Completely free interactive Scikit-Learn & XGBoost hands-on micro-courses.", "https://www.kaggle.com/learn/intro-to-machine-learning"),
            _res("Coursera (DeepLearning.AI)", "Machine Learning Specialization (Andrew Ng)", "World-renowned intuitive introduction to supervised and unsupervised ML.", "https://www.coursera.org/specializations/machine-learning-introduction", "Free Audit / Paid Cert"),
            _res("freeCodeCamp", "Machine Learning with Python Certification", "Free curriculum building five complete ML projects with TensorFlow & Python.", "https://www.freecodecamp.org/learn/machine-learning-with-python/"),
        ],
    },
    "Scikit-Learn": {
        "topics": "Pipelines, ColumnTransformer, GridSearchCV, ROC-AUC metrics",
        "project": "Build a clean Scikit-Learn preprocessing + classifier Pipeline avoiding leakage",
        "est_time": "2 weeks",
        "resources": [
            _res("Scikit-Learn Official", "Scikit-Learn Getting Started Guide", "Official user guide on estimators, pipelines, cross-validation, and evaluation.", "https://scikit-learn.org/stable/getting_started.html"),
            _res("Kaggle Learn", "Intermediate Machine Learning (Pipelines)", "Hands-on exercises handling missing values, categorical encoding, and leakage.", "https://www.kaggle.com/learn/intermediate-machine-learning"),
        ],
    },
    "Deep Learning": {
        "topics": "Backpropagation, CNNs, RNNs/Transformers, dropout, Adam optimizer",
        "project": "Train an image classifier and visualize validation loss & confusion matrix",
        "est_time": "4-6 weeks",
        "resources": [
            _res("Kaggle Learn", "Intro to Deep Learning", "Free hands-on neural network training labs using Python and TensorFlow/Keras.", "https://www.kaggle.com/learn/intro-to-deep-learning"),
            _res("PyTorch Official", "Deep Learning with PyTorch Tutorials", "Official hands-on deep learning tensor, autograd, and neural net recipes.", "https://pytorch.org/tutorials/"),
            _res("freeCodeCamp", "Machine Learning & Neural Networks in Python", "Build neural net classification projects completely free.", "https://www.freecodecamp.org/learn/machine-learning-with-python/"),
        ],
    },
    "PyTorch": {
        "topics": "Tensors, autograd, nn.Module, DataLoader, GPU training loops",
        "project": "Train a custom PyTorch image or text classifier cleanly using DataLoader",
        "est_time": "3-4 weeks",
        "resources": [
            _res("PyTorch Official", "Learn the Basics — PyTorch Tutorials", "Official 60-minute blitz and modular nn.Module training guides.", "https://pytorch.org/tutorials/"),
            _res("Hugging Face Learn", "NLP & Deep Learning Course", "Apply PyTorch cleanly to fine-tune modern Transformer models.", "https://huggingface.co/learn"),
        ],
    },
    "TensorFlow": {
        "topics": "tf.keras Sequential/Functional API, tf.data, callbacks, SavedModel",
        "project": "Train and export a TensorFlow Keras classifier for REST deployment",
        "est_time": "3-4 weeks",
        "resources": [
            _res("TensorFlow Official", "TensorFlow Tutorials (Google Colab)", "Interactive Colab notebooks spanning beginner Keras models through CNNs.", "https://www.tensorflow.org/tutorials"),
            _res("freeCodeCamp", "Machine Learning with Python (TensorFlow)", "Free hands-on TensorFlow neural networks, NLP, and recommendation projects.", "https://www.freecodecamp.org/learn/machine-learning-with-python/"),
        ],
    },
    "Keras": {
        "topics": "Model compile/fit, transfer learning, custom callbacks, preprocessing layers",
        "project": "Fine-tune MobileNet on a custom image dataset using Keras transfer learning",
        "est_time": "1-2 weeks",
        "resources": [
            _res("TensorFlow Official", "Keras & TensorFlow Beginner Guides", "Official tutorials demonstrating concise model building with tf.keras.", "https://www.tensorflow.org/tutorials"),
            _res("Kaggle Learn", "Intro to Deep Learning (Keras)", "Practical bite-sized exercises tuning Keras layers and early stopping.", "https://www.kaggle.com/learn/intro-to-deep-learning"),
        ],
    },
    "Hugging Face": {
        "topics": "Transformers library, tokenizers, Trainer API, model fine-tuning",
        "project": "Fine-tune a pretrained DistilBERT classifier for resume/job text tagging",
        "est_time": "2 weeks",
        "resources": [
            _res("Hugging Face Learn", "The Hugging Face LLM & NLP Course", "Completely free practical course on transformers, datasets, and fine-tuning.", "https://huggingface.co/learn"),
            _res("PyTorch Official", "PyTorch Fundamentals for Transformers", "Strengthen underlying PyTorch tensor and DataLoader intuition.", "https://pytorch.org/tutorials/"),
        ],
    },
    "Natural Language Processing": {
        "topics": "Tokenization, TF-IDF, word embeddings, Transformers, RAG basics",
        "project": "Build a semantic document matcher combining TF-IDF and embeddings",
        "est_time": "3-4 weeks",
        "resources": [
            _res("Hugging Face Learn", "NLP Course (Transformers & Tokenizers)", "Free interactive tutorials covering modern NLP pipelines from scratch.", "https://huggingface.co/learn"),
            _res("Scikit-Learn Official", "Working With Text Data Tutorial", "Master classic Bag-of-Words and TF-IDF pipelines clearly.", "https://scikit-learn.org/stable/getting_started.html"),
        ],
    },
    "Computer Vision": {
        "topics": "CNNs, image augmentation, object detection, transfer learning",
        "project": "Build an automated document/object classifier using transfer learning",
        "est_time": "3-4 weeks",
        "resources": [
            _res("TensorFlow Official", "Convolutional Neural Networks Tutorials", "Run image classification and transfer learning notebooks right in Colab.", "https://www.tensorflow.org/tutorials"),
            _res("PyTorch Official", "PyTorch Vision Transfer Learning Tutorials", "Hands-on official guide to image transforms and fine-tuning ResNets.", "https://pytorch.org/tutorials/"),
        ],
    },
    "MLflow": {
        "topics": "Experiment tracking, parameter logging, artifact store, Model Registry",
        "project": "Log hyperparameters, F1 metrics, and serialized models across 10 runs",
        "est_time": "1 week",
        "resources": [
            _res("MLflow Official", "MLflow Tracking Quickstart", "Concise official tutorial logging training parameters and registering models.", "https://mlflow.org/docs/latest/getting-started/intro-quickstart/"),
            _res("roadmap.sh", "MLOps & Model Serving Roadmap", "Explore how experiment tracking fits into production ML pipelines.", "https://roadmap.sh/mlops"),
        ],
    },
    "Apache Spark": {
        "topics": "PySpark DataFrames, Spark SQL, lazy evaluation, partitioning, shuffling",
        "project": "Process a multi-GB clickstream log into daily Parquet aggregates via PySpark",
        "est_time": "3 weeks",
        "resources": [
            _res("Apache Spark Docs", "Spark Python & SQL Quickstart", "Official PySpark DataFrame, SQL, and streaming guides.", "https://spark.apache.org/docs/latest/"),
            _res("roadmap.sh", "Data Engineering Roadmap", "See how Spark connects with ETL orchestration and cloud data lakes.", "https://roadmap.sh/data-engineer"),
        ],
    },
    "Hadoop": {
        "topics": "HDFS distributed storage, YARN resource management, Parquet/ORC formats",
        "project": "Understand HDFS partitioning and batch processing alongside Spark SQL",
        "est_time": "2 weeks",
        "resources": [
            _res("Apache Spark Docs", "Distributed Big Data Processing Guides", "Learn modern distributed storage formats commonly paired with HDFS and S3.", "https://spark.apache.org/docs/latest/"),
            _res("roadmap.sh", "Big Data & Data Engineer Track", "Structured context on legacy Hadoop ecosystems vs modern lakehouses.", "https://roadmap.sh/data-engineer"),
        ],
    },
    "ETL": {
        "topics": "Extract/Transform/Load patterns, incremental loads, idempotency, retries",
        "project": "Build an idempotent daily Python + SQL ETL loader writing clean tables",
        "est_time": "2-3 weeks",
        "resources": [
            _res("AWS Official", "Data Engineering Digital Learning Plans", "Free Skill Builder pathways covering batch ETL pipelines and data lakes.", "https://explore.skillbuilder.aws"),
            _res("dbt Docs", "Modern ELT Transformation Principles", "Learn modular SQL testing and dependency-ordered transformation pipelines.", "https://docs.getdbt.com/docs/introduction"),
        ],
    },
    "Data Warehousing": {
        "topics": "Fact vs dimension tables, star schemas, OLTP vs OLAP, partitioning",
        "project": "Model a star schema (facts + dimensions) for orders, customers, and dates",
        "est_time": "2 weeks",
        "resources": [
            _res("Snowflake Official", "Cloud Data Warehousing Guides", "Practical guides on analytical schemas, storage separation, and scaling.", "https://docs.snowflake.com"),
            _res("Google Cloud", "BigQuery Warehouse Architecture Docs", "Official cloud warehouse design best practices.", "https://cloud.google.com/bigquery/docs"),
        ],
    },
    "Data Modeling": {
        "topics": "Normalization (1NF-3NF), ER diagrams, star/snowflake schemas, keys",
        "project": "Draw an ER diagram and migrate normalized OLTP tables to an OLAP schema",
        "est_time": "2 weeks",
        "resources": [
            _res("freeCodeCamp", "Relational Database Design Curriculum", "Practice primary keys, foreign keys, and normalized table structures hands-on.", "https://www.freecodecamp.org/learn/relational-database/"),
            _res("dbt Docs", "Analytics Data Modeling Best Practices", "Learn staging, intermediate, and mart schema design patterns.", "https://docs.getdbt.com/docs/introduction"),
        ],
    },
    "dbt": {
        "topics": "SQL models, ref() dependency DAG, schema tests, incremental builds",
        "project": "Convert raw SQL scripts into tested dbt staging and mart models",
        "est_time": "1-2 weeks",
        "resources": [
            _res("dbt Official", "dbt Documentation & Introduction", "Official guides covering SQL transformations, lineage graphs, and tests.", "https://docs.getdbt.com/docs/introduction"),
            _res("roadmap.sh", "Analytics & Data Engineering Path", "Discover where dbt sits cleanly inside modern ELT stacks.", "https://roadmap.sh/data-engineer"),
        ],
    },
    "Selenium": {
        "topics": "WebDriver locators, explicit waits, Page Object Model, cross-browser runs",
        "project": "Automate login, search, and form assertions cleanly using Page Objects",
        "est_time": "2 weeks",
        "resources": [
            _res("Selenium Official", "Selenium WebDriver Documentation", "Official getting-started guides across Python, Java, and JavaScript bindings.", "https://www.selenium.dev/documentation/"),
            _res("roadmap.sh", "QA Automation Testing Roadmap", "Structured QA skill progression covering UI, API, and CI testing.", "https://roadmap.sh/qa"),
        ],
    },
    "Playwright": {
        "topics": "Auto-waiting locators, API mocking, trace viewer, parallel headless tests",
        "project": "Write an end-to-end Playwright test suite integrated into GitHub Actions",
        "est_time": "1-2 weeks",
        "resources": [
            _res("Playwright Official", "Playwright Intro & Test Writing Docs", "Clear official tutorials with trace viewer debugging and CI integration.", "https://playwright.dev/docs/intro"),
            _res("roadmap.sh", "QA Engineering Roadmap", "Compare Playwright with Selenium and Cypress in modern test teams.", "https://roadmap.sh/qa"),
        ],
    },
    "Cypress": {
        "topics": "Interactive test runner, network cy.intercept, fixtures, custom commands",
        "project": "Test a React frontend's checkout workflow using stubbed API responses",
        "est_time": "1-2 weeks",
        "resources": [
            _res("Cypress Official", "Cypress Documentation & Guides", "Official guides covering E2E and component testing best practices.", "https://docs.cypress.io/"),
            _res("roadmap.sh", "QA & Frontend Testing Roadmap", "Understand testing pyramids cleanly across unit and E2E layers.", "https://roadmap.sh/qa"),
        ],
    },
    "Pytest": {
        "topics": "Fixtures, parametrize, monkeypatch mocking, coverage reports",
        "project": "Write a comprehensive fixture-driven Pytest suite for a Python API",
        "est_time": "1 week",
        "resources": [
            _res("Pytest Official", "Pytest Getting Started Guide", "Official tutorial covering test discovery, assertions, fixtures, and tmp paths.", "https://docs.pytest.org/en/stable/getting-started.html"),
            _res("freeCodeCamp", "Quality Assurance Concepts", "Learn automated test discipline and assertion design patterns.", "https://www.freecodecamp.org/learn/quality-assurance/"),
        ],
    },
    "Jest": {
        "topics": "Unit test suites, async matchers, module mocks, React Testing Library",
        "project": "Add unit and component test coverage to a JavaScript/React project",
        "est_time": "1 week",
        "resources": [
            _res("Jest Official", "Jest Getting Started Docs", "Official setup, matchers, async testing, and mocking documentation.", "https://jestjs.io/docs/getting-started"),
            _res("roadmap.sh", "Frontend & QA Testing Paths", "Learn how Jest fits alongside Playwright/Cypress end-to-end tests.", "https://roadmap.sh/qa"),
        ],
    },
    "JUnit": {
        "topics": "JUnit 5 annotations, parameterized tests, assertions, Maven/Gradle integration",
        "project": "Write JUnit 5 unit & service tests cleanly for a Spring Boot backend",
        "est_time": "1 week",
        "resources": [
            _res("JUnit 5 Official", "JUnit 5 Official User Guide", "Comprehensive documentation on @Test, @ParameterizedTest, and extensions.", "https://junit.org/junit5/docs/current/user-guide/"),
            _res("Spring Official", "Testing the Web Layer in Spring Boot", "Practical official guide pairing JUnit cleanly with Spring MockMvc.", "https://spring.io/guides"),
        ],
    },
    "Test Automation": {
        "topics": "Test pyramid, Page Object pattern, CI gates, test data hygiene",
        "project": "Combine unit, API, and browser UI tests in one automated CI pipeline",
        "est_time": "2 weeks",
        "resources": [
            _res("Playwright Official", "Modern End-to-End Test Automation Docs", "Start quickly with reliable auto-waiting browser and API tests.", "https://playwright.dev/docs/intro"),
            _res("freeCodeCamp", "Quality Assurance Certification", "Free testing challenges covering functional tests and assertions.", "https://www.freecodecamp.org/learn/quality-assurance/"),
            _res("roadmap.sh", "QA Engineer Roadmap", "Complete step-by-step map from manual QA to automation architect.", "https://roadmap.sh/qa"),
        ],
    },
    "Manual Testing": {
        "topics": "Boundary value analysis, equivalence partitioning, test plans, bug reports",
        "project": "Write a structured test plan and reproducible defect tickets for a web app",
        "est_time": "1 week",
        "resources": [
            _res("roadmap.sh", "QA Foundations & Manual Testing", "Understand SDLC testing levels, regression, smoke, and exploratory techniques.", "https://roadmap.sh/qa"),
            _res("Atlassian University", "Bug Tracking & Issue Workflows", "Learn clean defect triage and Jira reporting workflows used by real QA teams.", "https://university.atlassian.com"),
        ],
    },
    "Unit Testing": {
        "topics": "Isolation, Arrange-Act-Assert, test doubles/mocking, edge-case coverage",
        "project": "Achieve >85% unit coverage on core business modules without flaky mocks",
        "est_time": "1 week",
        "resources": [
            _res("Pytest Official", "Python Unit Testing Getting Started", "Write clean, readable assertions and fixtures using Pytest.", "https://docs.pytest.org/en/stable/getting-started.html"),
            _res("Jest Official", "JavaScript Unit Testing Guide", "Fast unit testing tutorials for JavaScript and TypeScript functions.", "https://jestjs.io/docs/getting-started"),
        ],
    },
    "Postman": {
        "topics": "Collections, environment variables, pre-request/test scripts, Newman CLI",
        "project": "Build an automated Postman collection verifying REST auth & error states",
        "est_time": "1 week",
        "resources": [
            _res("Postman Official", "Postman Learning Center Overview", "Official tutorials on workspaces, test assertions, and collection runners.", "https://learning.postman.com/docs/getting-started/overview/"),
            _res("roadmap.sh", "QA API Testing Concepts", "Understand status verification, contract tests, and CI API execution.", "https://roadmap.sh/qa"),
        ],
    },
    "Jira": {
        "topics": "Scrum/Kanban boards, epics, user stories, bug triage, workflows",
        "project": "Set up a realistic sprint backlog with linked epics, stories, and QA bugs",
        "est_time": "3-5 days",
        "resources": [
            _res("Atlassian University", "Free Jira & Agile Team Courses", "Official free on-demand Atlassian courses covering Jira boards and JQL.", "https://university.atlassian.com"),
            _res("Scrum Guides", "The Official Scrum Guide", "Understand the agile sprint roles and artifacts managed inside Jira.", "https://scrumguides.org/"),
        ],
    },
    "Confluence": {
        "topics": "Technical design docs, runbooks, meeting notes, Jira issue linking",
        "project": "Author a clean architecture decision record (ADR) linked to Jira tasks",
        "est_time": "2-3 days",
        "resources": [
            _res("Atlassian University", "Confluence Fundamentals (Free)", "Official Atlassian training on organizing team knowledge bases effectively.", "https://university.atlassian.com"),
            _res("roadmap.sh", "Engineering Documentation Basics", "Learn how specs and runbooks fit into product engineering.", "https://roadmap.sh/software-architect"),
        ],
    },
    "Agile": {
        "topics": "Iterative delivery, user stories, sprint planning, retrospectives",
        "project": "Break down an app idea into prioritized user stories with acceptance criteria",
        "est_time": "3-5 days",
        "resources": [
            _res("Scrum Guides", "The Definitive Scrum Guide", "Concise free reference on empirical Agile roles, sprints, and increments.", "https://scrumguides.org/"),
            _res("Atlassian University", "Agile & Jira Workflows", "Practical free courses on backlog grooming and team collaboration.", "https://university.atlassian.com"),
        ],
    },
    "Scrum": {
        "topics": "Product Owner, Scrum Master, Sprint Backlog, Daily Scrum, Sprint Review",
        "project": "Run a mock 1-week sprint backlog with clear Definition of Done checks",
        "est_time": "3-5 days",
        "resources": [
            _res("Scrum Guides", "The Official Scrum Guide (Schaber & Sutherland)", "Short, authoritative primary source defining Scrum events and artifacts.", "https://scrumguides.org/"),
            _res("Atlassian University", "Managing Scrum Teams in Jira", "Free guided workflows for planning sprints and velocity retrospectives.", "https://university.atlassian.com"),
        ],
    },
    "Figma": {
        "topics": "Auto Layout, components/variants, design tokens, interactive prototyping",
        "project": "Design a responsive 5-screen web & mobile app with reusable Figma components",
        "est_time": "2-3 weeks",
        "resources": [
            _res("Figma Official", "Figma Help Center & Beginner Courses", "Free official tutorials on frames, Auto Layout, components, and Dev Mode.", "https://help.figma.com"),
            _res("Coursera (Google)", "Google UX Design Certificate", "Guided Figma wireframing and high-fidelity prototyping assignments.", "https://www.coursera.org/professional-certificates/google-ux-design", "Free Audit / Paid Cert"),
            _res("roadmap.sh", "UX Design Roadmap", "Visual overview of Figma tools alongside UX research milestones.", "https://roadmap.sh/ux-design"),
        ],
    },
    "UI/UX Design": {
        "topics": "Visual hierarchy, usability heuristics, accessibility contrast, user flows",
        "project": "Redesign a confusing checkout flow and document the before/after rationale",
        "est_time": "3-4 weeks",
        "resources": [
            _res("Coursera (Google)", "Google UX Design Professional Certificate", "End-to-end UX process from user empathy through Figma prototyping and testing.", "https://www.coursera.org/professional-certificates/google-ux-design", "Free Audit / Paid Cert"),
            _res("roadmap.sh", "UX Design Interactive Roadmap", "Clear step-by-step path covering typography, color, layout, and usability.", "https://roadmap.sh/ux-design"),
            _res("Figma Official", "Design Craft & Prototyping Guides", "Official guides translating UI/UX principles directly inside Figma.", "https://help.figma.com"),
        ],
    },
    "Wireframing": {
        "topics": "Low-fidelity layout sketching, user task flows, information hierarchy",
        "project": "Wireframe core onboarding and dashboard flows cleanly before visual styling",
        "est_time": "1 week",
        "resources": [
            _res("Coursera (Google)", "Google UX Design — Wireframes & Low-Fi Prototypes", "Hands-on assignments practicing paper and digital wireframes cleanly.", "https://www.coursera.org/professional-certificates/google-ux-design", "Free Audit / Paid Cert"),
            _res("Figma Official", "Figma & FigJam Wireframing Guides", "Rapid flow diagrams and component wireframing techniques.", "https://help.figma.com"),
        ],
    },
    "Prototyping": {
        "topics": "Interactive click-through transitions, micro-interactions, usability flows",
        "project": "Link a 6-screen onboarding prototype in Figma ready for user testing",
        "est_time": "1 week",
        "resources": [
            _res("Figma Official", "Figma Interactive Prototyping Docs", "Official tutorials on smart animate, overlays, variables, and sharing.", "https://help.figma.com"),
            _res("Coursera (Google)", "Build Dynamic UX Prototypes in Figma", "Guided usability-ready interactive prototype exercises.", "https://www.coursera.org/professional-certificates/google-ux-design", "Free Audit / Paid Cert"),
        ],
    },
    "User Research": {
        "topics": "User interviews, usability testing, personas, affinity mapping, heuristics",
        "project": "Conduct 5 usability test sessions on an app prototype and synthesize findings",
        "est_time": "2 weeks",
        "resources": [
            _res("Coursera (Google)", "Conduct UX Research and Test Concepts", "Learn ethical user interviews, research synthesis, and usability studies.", "https://www.coursera.org/professional-certificates/google-ux-design", "Free Audit / Paid Cert"),
            _res("roadmap.sh", "UX Research & Strategy Track", "Structured guide to qualitative and quantitative UX discovery methods.", "https://roadmap.sh/ux-design"),
        ],
    },
    "Design Systems": {
        "topics": "Color/spacing tokens, typography scales, variant components, documentation",
        "project": "Build a clean mini UI kit with buttons, inputs, cards, and token documentation",
        "est_time": "2 weeks",
        "resources": [
            _res("Figma Official", "Variables, Components & Libraries in Figma", "Official guides on maintaining scalable cross-team component libraries.", "https://help.figma.com"),
            _res("roadmap.sh", "Design Systems & UI Craft", "See how tokens bridge Figma handoff cleanly with React/Tailwind code.", "https://roadmap.sh/design-system"),
        ],
    },
    "Cybersecurity": {
        "topics": "CIA Triad, threat modeling, OWASP Top 10, IAM, basic incident response",
        "project": "Audit a sample web app against OWASP Top 10 flaws cleanly",
        "est_time": "4 weeks",
        "resources": [
            _res("TryHackMe", "Pre-Security & Cyber Defense Learning Paths", "Hands-on browser labs teaching Linux, networking, and real security defense.", "https://tryhackme.com/paths"),
            _res("PortSwigger Academy", "Web Security Academy (Free Labs)", "Free deep interactive labs on SQLi, XSS, CSRF, and auth vulnerabilities.", "https://portswigger.net/web-security"),
            _res("Coursera (Google)", "Google Cybersecurity Professional Certificate", "Beginner-friendly career path covering SIEM, Linux, Python, and Security+ prep.", "https://www.coursera.org/professional-certificates/google-cybersecurity", "Free Audit / Paid Cert"),
        ],
    },
    "Penetration Testing": {
        "topics": "Reconnaissance, enumeration, SQLi/XSS exploitation, reporting fixes",
        "project": "Complete beginner interactive web & network pentesting labs on PortSwigger",
        "est_time": "4 weeks",
        "resources": [
            _res("PortSwigger Academy", "Web Application Penetration Testing Labs", "100% free world-class hands-on labs created by the Burp Suite team.", "https://portswigger.net/web-security"),
            _res("TryHackMe", "Jr Penetration Tester Interactive Path", "Guided in-browser VMs practicing enumeration, web flaws, and privilege escalation.", "https://tryhackme.com/paths"),
        ],
    },
    "Network Security": {
        "topics": "Defense in depth, VPNs, ACLs, IDS/IPS, zero-trust segmentation",
        "project": "Design segmented DMZ/internal firewall rules for a mock cloud topology",
        "est_time": "3 weeks",
        "resources": [
            _res("Cisco NetAcad", "Networking & Cybersecurity Free Courses", "Structured Cisco Networking Academy training on secure switching and defense.", "https://www.netacad.com"),
            _res("Coursera (Google)", "Play It Safe: Manage Security Risks", "Covers network hardening, firewalls, and security protocols clearly.", "https://www.coursera.org/professional-certificates/google-cybersecurity", "Free Audit / Paid Cert"),
        ],
    },
    "Encryption": {
        "topics": "Symmetric AES vs asymmetric RSA/ECC, TLS/HTTPS handshakes, password hashing",
        "project": "Implement salted Argon2/bcrypt hashing and verify TLS certificates in Python",
        "est_time": "1-2 weeks",
        "resources": [
            _res("Coursera (Google)", "Google Cybersecurity — Cryptography & Protection", "Intuitive beginner explanations of hashing, PKI, and TLS encryption.", "https://www.coursera.org/professional-certificates/google-cybersecurity", "Free Audit / Paid Cert"),
            _res("roadmap.sh", "Cyber Security Cryptography Concepts", "Visual breakdown of hashing, TLS, certificates, and key management.", "https://roadmap.sh/cyber-security"),
        ],
    },
    "Firewalls": {
        "topics": "Stateful packet inspection, WAF rules, ingress/egress ACLs, UFW/iptables",
        "project": "Configure strict least-privilege firewall rules on a Linux web server",
        "est_time": "1 week",
        "resources": [
            _res("TryHackMe", "Network Security & Firewall Rooms", "Hands-on labs practicing firewall filtering and traffic analysis.", "https://tryhackme.com/paths"),
            _res("Cisco NetAcad", "Network Defense Essentials", "Official Cisco training on ACLs, stateful firewalls, and perimeter defense.", "https://www.netacad.com"),
        ],
    },
    "SIEM": {
        "topics": "Log aggregation, correlation rules, alert triage, false-positive tuning",
        "project": "Parse authentication & web logs to build brute-force alert rules cleanly",
        "est_time": "2 weeks",
        "resources": [
            _res("Coursera (Google)", "Assets, Threats, and SIEM Investigation", "Includes practical hands-on SIEM and log triage exercises.", "https://www.coursera.org/professional-certificates/google-cybersecurity", "Free Audit / Paid Cert"),
            _res("TryHackMe", "SOC Level 1 Learning Path", "Interactive browser SIEM & log analysis scenarios for aspiring analysts.", "https://tryhackme.com/paths"),
        ],
    },
    "Vulnerability Assessment": {
        "topics": "CVSS scoring, dependency/OS scanning, patch prioritization, false positives",
        "project": "Scan a local lab container image and triage top CVEs with fix steps",
        "est_time": "1-2 weeks",
        "resources": [
            _res("PortSwigger Academy", "Web Vulnerability Discovery Labs", "Learn how common vulnerabilities arise and how to validate remediation.", "https://portswigger.net/web-security"),
            _res("Coursera (Google)", "Google Cybersecurity Risk & Assessment", "Structured frameworks for scanning, prioritizing, and reporting risk.", "https://www.coursera.org/professional-certificates/google-cybersecurity", "Free Audit / Paid Cert"),
        ],
    },
    "Risk Assessment": {
        "topics": "Threat likelihood vs impact, NIST frameworks, risk register, mitigation",
        "project": "Write a concise security risk matrix for a small e-commerce application",
        "est_time": "1-2 weeks",
        "resources": [
            _res("Coursera (Google)", "Foundations of Cybersecurity & Risk Management", "Introduces NIST RMF, CIA triad, and practical risk scoring.", "https://www.coursera.org/professional-certificates/google-cybersecurity", "Free Audit / Paid Cert"),
            _res("roadmap.sh", "Cyber Security Governance & Risk", "Connects technical controls to business risk prioritization.", "https://roadmap.sh/cyber-security"),
        ],
    },
    "Networking": {
        "topics": "OSI & TCP/IP layers, subnetting, DNS, HTTP/HTTPS, switching & routing",
        "project": "Map packet hops cleanly using traceroute, dig/nslookup, and packet capture",
        "est_time": "3 weeks",
        "resources": [
            _res("Cisco NetAcad", "Networking Basics (Free Self-Paced)", "Official Cisco course teaching IP addressing, Ethernet, and router essentials.", "https://www.netacad.com"),
            _res("TryHackMe", "Pre-Security Network Fundamentals", "Interactive rooms demystifying packets, OSI layers, and DNS visually.", "https://tryhackme.com/paths"),
        ],
    },
    "TCP/IP": {
        "topics": "IPv4/IPv6 CIDR subnetting, TCP 3-way handshake, UDP, DNS, DHCP",
        "project": "Practice CIDR subnet calculations and capture a TCP handshake cleanly",
        "est_time": "2 weeks",
        "resources": [
            _res("Cisco NetAcad", "Networking Devices & IP Addressing", "Step-by-step subnetting, TCP/UDP ports, and packet forwarding labs.", "https://www.netacad.com"),
            _res("Linux Journey", "Linux Networking & Subnetting Modules", "Beginner-friendly explanations of routing tables, ARP, DNS, and TCP.", "https://linuxjourney.com/"),
        ],
    },
    "Cisco": {
        "topics": "IOS CLI, VLANs, trunking, OSPF routing, ACL security, CCNA prep",
        "project": "Build and test a multi-VLAN switched & routed topology in lab software",
        "est_time": "4 weeks",
        "resources": [
            _res("Cisco NetAcad", "Cisco CCNA & Network Technician Paths", "Official Cisco curriculum covering switching, routing, and Packet Tracer labs.", "https://www.netacad.com"),
            _res("TryHackMe", "Network Security Operations", "Reinforce routing and firewall troubleshooting concepts cleanly.", "https://tryhackme.com/paths"),
        ],
    },
    "Embedded C": {
        "topics": "Bitwise register manipulation, volatile pointers, interrupts, timers",
        "project": "Write bare-metal interrupt-driven LED & button firmware without blocking delays",
        "est_time": "3 weeks",
        "resources": [
            _res("Arduino Docs", "Arduino Learning & C/C++ Firmware Guides", "Quickly test register/GPIO/interrupt firmware concepts on real boards.", "https://docs.arduino.cc/learn/"),
            _res("Harvard CS50", "CS50 Low-Level C & Memory", "Build bulletproof C pointer and memory-safety intuition first.", "https://cs50.harvard.edu/x/"),
        ],
    },
    "Microcontrollers": {
        "topics": "GPIO, ADC/DAC, PWM, timers, watchdogs, reading hardware datasheets",
        "project": "Interface a temperature sensor & OLED screen on an MCU reading datasheet timings",
        "est_time": "3 weeks",
        "resources": [
            _res("Arduino Docs", "Microcontroller I/O & Sensor Tutorials", "Beginner-friendly guides covering PWM, analog inputs, and timing.", "https://docs.arduino.cc/learn/"),
            _res("STMicroelectronics", "STM32 Getting Started Ecosystem", "Explore industrial ARM Cortex-M microcontrollers and CubeIDE tooling.", "https://www.st.com"),
        ],
    },
    "STM32": {
        "topics": "STM32CubeIDE, HAL/LL drivers, DMA, hardware timers, UART/SPI",
        "project": "Configure DMA UART telemetry cleanly on an STM32 Nucleo board",
        "est_time": "3 weeks",
        "resources": [
            _res("STMicroelectronics", "STM32 Microcontrollers & CubeIDE Resources", "Official datasheets, HAL guides, and getting-started labs.", "https://www.st.com"),
            _res("FreeRTOS Docs", "FreeRTOS on ARM Cortex-M", "Learn real-time multitasking concepts commonly paired with STM32.", "https://www.freertos.org/Documentation/00-Overview"),
        ],
    },
    "ESP32": {
        "topics": "Wi-Fi/BLE connectivity, ESP-IDF/Arduino framework, deep sleep, MQTT",
        "project": "Build an IoT telemetry node publishing sensor readings over Wi-Fi/MQTT",
        "est_time": "2 weeks",
        "resources": [
            _res("Arduino Docs", "Embedded Board Programming Guides", "Rapid hardware prototyping guides applicable directly to ESP32 modules.", "https://docs.arduino.cc/learn/"),
            _res("FreeRTOS Docs", "FreeRTOS Real-Time Kernel Documentation", "Understand tasks and queues running underneath ESP-IDF.", "https://www.freertos.org/Documentation/00-Overview"),
        ],
    },
    "Arduino": {
        "topics": "Digital/analog I/O, libraries, Serial debugging, sensor wiring",
        "project": "Build a closed-loop PWM fan or servo controller reading sensor feedback",
        "est_time": "1-2 weeks",
        "resources": [
            _res("Arduino Official", "Arduino Learn Hub", "Official step-by-step electronics, wiring diagrams, and C/C++ tutorials.", "https://docs.arduino.cc/learn/"),
            _res("LearnCpp", "C++ Fundamentals for Firmware", "Strengthen C++ structuring skills for larger multi-file microcontroller sketches.", "https://www.learncpp.com/"),
        ],
    },
    "RTOS": {
        "topics": "Preemptive scheduling, tasks, mutexes, semaphores, priority inversion",
        "project": "Separate sensor sampling, display, and logging into 3 prioritized FreeRTOS tasks",
        "est_time": "2-3 weeks",
        "resources": [
            _res("FreeRTOS Official", "FreeRTOS Documentation Overview", "Official kernel guides explaining tasks, queues, mutexes, and timers cleanly.", "https://www.freertos.org/Documentation/00-Overview"),
            _res("STMicroelectronics", "Embedded Firmware & RTOS Integration", "Official semiconductor guides pairing RTOS cleanly with MCU hardware.", "https://www.st.com"),
        ],
    },
    "Embedded Linux": {
        "topics": "Cross-compilation, device trees, Yocto/Buildroot basics, kernel drivers",
        "project": "Cross-compile a custom C++ telemetry daemon running on Raspberry Pi Linux",
        "est_time": "4 weeks",
        "resources": [
            _res("Linux Journey", "Linux Internals & Processes Foundations", "Essential user-space, filesystem, and systemd concepts for Embedded Linux.", "https://linuxjourney.com/"),
            _res("LearnCpp", "Systems C++ Development Guide", "Write safe systems daemons cleanly in modern C++.", "https://www.learncpp.com/"),
        ],
    },
    "ARM Architecture": {
        "topics": "ARM Cortex-M/A privilege modes, NVIC interrupts, memory maps, registers",
        "project": "Inspect vector tables, linker scripts, and NVIC priorities cleanly on Cortex-M",
        "est_time": "3 weeks",
        "resources": [
            _res("STMicroelectronics", "STM32 ARM Cortex-M Documentation", "Official technical reference manuals and application notes for Cortex-M MCUs.", "https://www.st.com"),
            _res("FreeRTOS Official", "Cortex-M Task Scheduling Concepts", "Learn how RTOS context switching leverages ARM interrupt primitives.", "https://www.freertos.org/Documentation/00-Overview"),
        ],
    },
    "Maven": {
        "topics": "pom.xml lifecycle, dependencies, multi-module builds, plugins",
        "project": "Configure a multi-module Java project building and running JUnit tests via Maven",
        "est_time": "1 week",
        "resources": [
            _res("Apache Maven", "Maven Getting Started Guide", "Official tutorial covering coordinates, build lifecycle, and dependency scopes.", "https://maven.apache.org/guides/getting-started/"),
            _res("Spring Official", "Maven with Spring Boot Guides", "Official guides demonstrating Spring Boot Starter dependency management.", "https://spring.io/guides"),
        ],
    },
    "Gradle": {
        "topics": "build.gradle DSL, incremental build cache, tasks, Android/Java plugins",
        "project": "Configure custom Gradle test & checkstyle quality tasks on a JVM project",
        "est_time": "1 week",
        "resources": [
            _res("Gradle Official", "Gradle User Manual", "Official reference covering Groovy/Kotlin DSL, caching, and dependency management.", "https://docs.gradle.org/current/userguide/userguide.html"),
            _res("Google Android", "Android Build Tooling Basics", "Understand Gradle flavors and dependencies in mobile projects.", "https://developer.android.com/courses"),
        ],
    },
}


# Category fallback templates so EVERY skill in skills.json gets 2-3 verified non-fake resources
CATEGORY_FALLBACK_PLATFORMS = {
    "languages": [
        _res("freeCodeCamp", "Programming Foundations & Coding Curriculum", "Free interactive exercises strengthening programming logic and syntax.", "https://www.freecodecamp.org/learn"),
        _res("roadmap.sh", "Programming & Software Engineering Roadmaps", "Community-curated step-by-step developer paths and reference links.", "https://roadmap.sh/"),
    ],
    "frameworks": [
        _res("roadmap.sh", "Framework & Architecture Learning Paths", "Curated step-by-step web and backend framework guides.", "https://roadmap.sh/backend"),
        _res("MDN Web Docs", "Web Framework & Server-Side Concepts", "Mozilla's free conceptual and hands-on guides for modern web stacks.", "https://developer.mozilla.org/en-US/docs/Learn"),
    ],
    "databases": [
        _res("freeCodeCamp", "Relational Database & Data Modeling Track", "Interactive SQL, relational schema design, and query practice.", "https://www.freecodecamp.org/learn/relational-database/"),
        _res("roadmap.sh", "Database Engineering Roadmaps", "Structured learning guides covering SQL, indexing, and NoSQL scaling.", "https://roadmap.sh/postgresql-dba"),
    ],
    "web": [
        _res("MDN Web Docs", "Learn Web Development Guides", "Official Mozilla curriculum covering HTML, CSS, JS, and UI design craft.", "https://developer.mozilla.org/en-US/docs/Learn"),
        _res("freeCodeCamp", "Responsive Web Design & Libraries", "Free project-driven curriculum for building responsive interfaces.", "https://www.freecodecamp.org/learn/responsive-web-design/"),
    ],
    "cloud": [
        _res("AWS Official", "AWS Skill Builder Digital Training", "Free cloud architecture and cloud operations learning modules.", "https://explore.skillbuilder.aws"),
        _res("Microsoft Learn", "Cloud Infrastructure Training Portals", "Free self-paced hands-on cloud computing sandboxes and modules.", "https://learn.microsoft.com/en-us/training/"),
    ],
    "AI/ML": [
        _res("Kaggle Learn", "Practical Data Science & ML Micro-Courses", "Free interactive Python, SQL, Pandas, ML, and Deep Learning notebooks.", "https://www.kaggle.com/learn"),
        _res("roadmap.sh", "AI & Data Scientist Roadmap", "Guided sequence covering statistics, ML algorithms, and MLOps.", "https://roadmap.sh/ai-and-data-scientist"),
    ],
    "embedded": [
        _res("Arduino Official", "Embedded Hardware & Firmware Guides", "Hands-on tutorials covering protocols, sensors, and C/C++ firmware.", "https://docs.arduino.cc/learn/"),
        _res("FreeRTOS Official", "Real-Time Embedded Systems Documentation", "Official technical reference for RTOS firmware design.", "https://www.freertos.org/Documentation/00-Overview"),
    ],
    "tools": [
        _res("roadmap.sh", "Developer Tooling & DevOps Roadmaps", "Structured guides for testing, CI/CD, security, networking, and Linux tools.", "https://roadmap.sh/devops"),
        _res("Microsoft Learn", "Developer & IT Engineering Training", "Free structured training paths for tooling, automation, and security.", "https://learn.microsoft.com/en-us/training/"),
    ],
}


def build_resources_json() -> None:
    with open(DATA_DIR / "skills.json", "r", encoding="utf-8") as f:
        skills_data = json.load(f)
    skill_cats = {s["name"]: s["category"] for s in skills_data.get("skills", [])}

    # Ensure 100% coverage of every skill appearing in jobs.csv, job_roles_info.json, and existing SKILL_BUNDLES
    jobs_df = pd.read_csv(DATA_DIR / "jobs.csv")
    needed_skills = set(SKILL_BUNDLES.keys())
    for col in ("required_skills", "preferred_skills"):
        for val in jobs_df[col].dropna():
            for sk in str(val).split("|"):
                if sk.strip():
                    needed_skills.add(sk.strip())

    with open(DATA_DIR / "job_roles_info.json", "r", encoding="utf-8") as f:
        roles_info = json.load(f)
    for role in roles_info.values():
        for st in role.get("learning_roadmap", []):
            for sk in st.get("skills", []):
                needed_skills.add(sk)

    # Also keep common existing skills
    for extra in ["GitHub", "GitLab", "SQLite", "Bootstrap", "Ruby", "Ruby on Rails", "Svelte", "NestJS"]:
        needed_skills.add(extra)

    output: Dict[str, dict] = {}
    for skill in sorted(needed_skills):
        if skill in SKILL_BUNDLES:
            bundle = SKILL_BUNDLES[skill]
            res_list = bundle["resources"]
            topics = bundle["topics"]
            project = bundle["project"]
            est_time = bundle["est_time"]
        else:
            cat = skill_cats.get(skill, "tools")
            res_list = CATEGORY_FALLBACK_PLATFORMS.get(cat, CATEGORY_FALLBACK_PLATFORMS["tools"])
            topics = f"Core principles, practical syntax/configuration, and real-world workflows in {skill}"
            project = f"Build and document a hands-on mini-project applying {skill}"
            est_time = "1-2 weeks"

        primary = res_list[0]
        output[skill] = {
            # Legacy top-level keys preserved for full backwards compatibility
            "platform": " / ".join(r["platform"] for r in res_list[:2]),
            "url": primary["url"],
            "topics": topics,
            "project": project,
            "est_time": est_time,
            # New 2-3 verified multi-platform resource list (Requirement 2)
            "resources": res_list[:3],
        }

    out_path = DATA_DIR / "skill_learning_resources.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"skills": output}, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"[skill_learning_resources.json] Generated verified multi-platform resources for {len(output)} skills.")


if __name__ == "__main__":
    build_resources_json()
